# -*- coding: utf-8 -*-
"""
Utility functions for sandbox executor.
"""

import re
import subprocess
import logging
from typing import Set, Dict, Any, Optional, Tuple

from app.core.executor.constants import CONTAINER_OWNER
from app.config.settings import ExecutorConfig

logger = logging.getLogger(__name__)


def find_available_port(port_min: int, port_max: int) -> int:
    """
    Find an available port in the defined range.
    
    Args:
        port_min: Minimum port number
        port_max: Maximum port number
    
    Returns:
        int: An available port number
        
    Raises:
        RuntimeError: If no ports are available
    """
    try:
        docker_used_ports = get_docker_used_ports()
        
        for port in range(port_min, port_max + 1):
            if port not in docker_used_ports:
                logger.info(f"Selected available port: {port}")
                return port
                
        raise RuntimeError(f"No available ports in range {port_min}-{port_max}")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Error checking Docker ports: {e.stderr or e}")
        raise


def find_available_ports() -> Tuple[int, int]:
    """
    Find available ports for both API and code services.
    
    Returns:
        Tuple[int, int]: (api_port, code_port)
        
    Raises:
        RuntimeError: If no ports are available
    """
    api_port = find_available_port(
        ExecutorConfig.API_PORT_RANGE_MIN, 
        ExecutorConfig.API_PORT_RANGE_MAX
    )
    code_port = find_available_port(
        ExecutorConfig.CODE_PORT_RANGE_MIN, 
        ExecutorConfig.CODE_PORT_RANGE_MAX
    )
    return api_port, code_port


def get_docker_used_ports() -> Set[int]:
    """
    Get all ports used by Docker containers with our label.
    
    Returns:
        Set[int]: Set of port numbers in use
    """
    docker_used_ports = set()
    cmd = [
        "docker", "ps",
        "--filter", f"label=owner={CONTAINER_OWNER}",
        "--format", "{{.Ports}}",
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)

    # Match all port mappings like 0.0.0.0:10001->8080/tcp
    port_pattern = r"0\.0\.0\.0:(\d+)->"
    for line in result.stdout.splitlines():
        docker_used_ports.update(
            int(p)
            for p in re.findall(port_pattern, line)
        )

    return docker_used_ports


def check_container_exists(container_name: str) -> bool:
    """
    Check if container exists and is owned by us.
    
    Args:
        container_name: Name of the container
        
    Returns:
        bool: True if container exists and is owned by us
    """
    try:
        cmd = [
            "docker", "ps", "-a",
            "--filter", f"name=^{container_name}$",
            "--filter", f"label=owner={CONTAINER_OWNER}",
            "--format", "{{.Names}}",
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return container_name in result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Error checking container: {e.stderr}")
        return False


def check_container_running(container_name: str) -> bool:
    """
    Check if container is running.
    
    Args:
        container_name: Name of the container
        
    Returns:
        bool: True if container is running
    """
    try:
        cmd = [
            "docker", "ps",
            "--filter", f"name=^{container_name}$",
            "--filter", f"label=owner={CONTAINER_OWNER}",
            "--format", "{{.Names}}",
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return container_name in result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Error checking container status: {e.stderr}")
        return False


def get_container_port(container_name: str) -> Optional[int]:
    """
    Get the API host port mapped to a container (for backward compatibility).
    
    Args:
        container_name: Name of the container
        
    Returns:
        Optional[int]: Host API port or None if not found
    """
    ports = get_container_ports(container_name)
    return ports.get("api_port") if ports else None


def get_container_ports(container_name: str) -> Optional[Dict[str, int]]:
    """
    Get all host ports mapped to a container.
    
    Args:
        container_name: Name of the container
        
    Returns:
        Optional[Dict[str, int]]: Dict with api_port and code_port, or None if not found
    """
    try:
        cmd = [
            "docker", "ps",
            "--filter", f"name=^{container_name}$",
            "--format", "{{.Ports}}",
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # Match pattern: 0.0.0.0:10001->8080/tcp, 0.0.0.0:20001->80/tcp
        port_pattern = r"0\.0\.0\.0:(\d+)->(\d+)/tcp"
        ports = {}
        
        for line in result.stdout.splitlines():
            for match in re.finditer(port_pattern, line):
                host_port = int(match.group(1))
                container_port = int(match.group(2))
                
                # Map by internal port
                if container_port == 8080:  # API port
                    ports["api_port"] = host_port
                elif container_port == 80:  # Code service port
                    ports["code_port"] = host_port
                    
        return ports if ports else None
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Error getting container ports: {e.stderr}")
        return None


def delete_container(container_name: str, force: bool = True) -> Dict[str, Any]:
    """
    Stop and remove a Docker container.
    
    Args:
        container_name: Name of the container
        force: Force removal even if running
        
    Returns:
        dict: Result with status and optional error message
    """
    try:
        # Check ownership first
        if not check_container_exists(container_name):
            return {
                "status": "failed",
                "error_msg": f"Container '{container_name}' not found or not owned by us"
            }
        
        # Stop and remove container
        if force:
            cmd = f"docker rm -f {container_name}"
        else:
            cmd = f"docker stop {container_name} && docker rm {container_name}"
        
        subprocess.run(cmd, shell=True, check=True, capture_output=True)
        logger.info(f"Deleted Docker container '{container_name}'")
        return {"status": "success"}
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Docker error deleting container '{container_name}': {e.stderr}")
        return {"status": "failed", "error_msg": f"Docker error: {e.stderr}"}
    except Exception as e:
        logger.error(f"Error deleting container '{container_name}': {e}")
        return {"status": "failed", "error_msg": str(e)}


def list_containers() -> Dict[str, Any]:
    """
    List all containers owned by us.
    
    Returns:
        dict: Result with status and container list
    """
    try:
        cmd = [
            "docker", "ps", "-a",
            "--filter", f"label=owner={CONTAINER_OWNER}",
            "--format", "{{.Names}}|{{.Status}}|{{.Ports}}|{{.Labels}}",
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        containers = []
        for line in result.stdout.splitlines():
            if line.strip():
                parts = line.split("|")
                if len(parts) >= 3:
                    containers.append({
                        "name": parts[0],
                        "status": parts[1],
                        "ports": parts[2],
                    })
        
        return {"status": "success", "containers": containers}
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Error listing containers: {e.stderr}")
        return {"status": "failed", "error_msg": str(e.stderr), "containers": []}


def generate_container_name(session_id: str) -> str:
    """
    Generate a container name from session ID.
    
    Args:
        session_id: Session identifier
        
    Returns:
        str: Container name
    """
    # Sanitize session_id for Docker container naming
    safe_id = session_id.replace("-", "").replace("_", "")[:12]
    return f"sandbox_{safe_id}"

