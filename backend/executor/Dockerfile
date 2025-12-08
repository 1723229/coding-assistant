# =============================================================================
# Executor Docker Image - Claude Code 沙箱执行环境
# =============================================================================
#
# 用途：
#   为 Claude Code 提供完整的沙箱执行环境，每个会话独立运行在自己的容器中
#
# 包含环境：
#   - Python 3.11
#   - nvm (Node Version Manager)
#   - Node.js LTS (v20) - 默认版本
#   - Node.js v14 - 兼容旧项目
#   - JDK 1.8 (Eclipse Temurin)
#   - Maven 3.9.6
#   - npx (随 Node.js 安装)
#   - claude-code CLI (@anthropic-ai/claude-code)
#   - yarn, pnpm
#
# 端口说明：
#   - 8080: FastAPI executor 服务 (内部端口，映射到外部 10001-10100)
#   - 3000: 预留给 repo 代码服务 (内部端口，映射到外部 20001-20100)
#          注：代码服务由 repo 自己的启动脚本管理，不在此镜像启动
#
# 构建命令：
#   cd /path/to/coding-assistant
#   docker build  -f backend/executor/Dockerfile -t coding-assistant-executor:latest .
#
# 环境变量（运行时由 ContainerManager 注入）：
#   - ANTHROPIC_API_KEY: Claude API 密钥
#   - ANTHROPIC_BASE_URL: API 基础 URL（可选）
#   - ANTHROPIC_MODEL: 使用的模型（可选）
#   - SESSION_ID: 会话标识
#   - WORKSPACE_PATH: 工作区路径（默认 /workspace）
#
# =============================================================================

FROM python:3.11-slim

# 基础环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Shanghai
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV WORKSPACE_PATH=/workspace
ENV PYTHONUNBUFFERED=1
ENV CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1

# =============================================================================
# 系统依赖安装
# =============================================================================
RUN apt-get update && apt-get install -y \
    # 基础工具
    git \
    curl \
    wget \
    vim \
    nano \
    build-essential \
    ca-certificates \
    gnupg \
    lsb-release \
    unzip \
    zip \
    tar \
    gzip \
    bzip2 \
    xz-utils \
    procps \
    locales \
    fontconfig \
    openssh-client \
    # Claude Agent SDK 需要的网络/系统工具
    lsof \
    net-tools \
    iproute2 \
    iputils-ping \
    dnsutils \
    telnet \
    netcat-openbsd \
    file \
    tree \
    htop \
    less \
    jq \
    # 编译工具
    make \
    gcc \
    g++ \
    # Playwright/Chrome 需要的依赖
    xvfb \
    dbus \
    dbus-x11 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgtk-3-0 \
    libx11-xcb1 \
    libxcb-dri3-0 \
    libxshmfence1 \
    libglu1-mesa \
    && rm -rf /var/lib/apt/lists/*

# 生成 locale
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && locale-gen

# =============================================================================
# JDK 8 安装 (Eclipse Temurin)
# =============================================================================
RUN mkdir -p /opt/java && \
    ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then \
        JDK_URL="https://github.com/adoptium/temurin8-binaries/releases/download/jdk8u392-b08/OpenJDK8U-jdk_x64_linux_hotspot_8u392b08.tar.gz"; \
    elif [ "$ARCH" = "arm64" ]; then \
        JDK_URL="https://github.com/adoptium/temurin8-binaries/releases/download/jdk8u392-b08/OpenJDK8U-jdk_aarch64_linux_hotspot_8u392b08.tar.gz"; \
    else \
        echo "Unsupported architecture: $ARCH" && exit 1; \
    fi && \
    wget -q "$JDK_URL" -O /tmp/openjdk.tar.gz && \
    tar -xzf /tmp/openjdk.tar.gz -C /opt/java --strip-components=1 && \
    rm /tmp/openjdk.tar.gz

ENV JAVA_HOME=/opt/java
ENV PATH="${JAVA_HOME}/bin:${PATH}"
RUN java -version

# =============================================================================
# Maven 安装
# =============================================================================
ENV MAVEN_VERSION=3.9.6
RUN wget -q https://archive.apache.org/dist/maven/maven-3/${MAVEN_VERSION}/binaries/apache-maven-${MAVEN_VERSION}-bin.tar.gz \
    && tar -xzf apache-maven-${MAVEN_VERSION}-bin.tar.gz -C /opt \
    && rm apache-maven-${MAVEN_VERSION}-bin.tar.gz \
    && ln -s /opt/apache-maven-${MAVEN_VERSION} /opt/maven

ENV MAVEN_HOME=/opt/maven
ENV PATH="${MAVEN_HOME}/bin:${PATH}"
RUN mvn --version

# =============================================================================
# nvm 和 Node.js 安装
# =============================================================================
ENV NVM_DIR=/root/.nvm
SHELL ["/bin/bash", "-c"]

# 安装 nvm
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash

# 安装 Node.js v20 (LTS) 和 v14，默认使用 v20
RUN source "$NVM_DIR/nvm.sh" \
    && nvm install 20 \
    && nvm install 14 \
    && nvm alias default 20 \
    && nvm use default \
    && npm install -g @anthropic-ai/claude-code \
    && npm install -g @fission-ai/openspec@latest \
    && npm install -g yarn \
    && npm install -g pnpm \
    && nvm install 14 \
    && npm install -g yarn \
    && npm install -g pnpm \
    && nvm use default

# 配置 bash 加载 nvm
RUN echo 'export NVM_DIR="/root/.nvm"' >> /root/.bashrc \
    && echo '[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"' >> /root/.bashrc \
    && echo '[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"' >> /root/.bashrc

# 设置 PATH（非交互式 shell）
ENV PATH="/root/.nvm/versions/node/v20.19.6/bin:${PATH}"
RUN node --version && npm --version && npx --version

# =============================================================================
# Playwright MCP 安装 (用于 MCP 浏览器自动化)
# =============================================================================
# 全局安装 @playwright/mcp 避免每次 npx 下载
# 同时安装 playwright 和 Chromium 浏览器
RUN source "$NVM_DIR/nvm.sh" \
    && npm install -g @playwright/mcp@latest \
    && npx playwright install chromium \
    && npx playwright install-deps chromium

# 设置 Playwright 环境变量，确保浏览器可被找到
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright
# 禁用 Playwright 的浏览器下载提示
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
# 验证 Chromium 已安装
RUN source "$NVM_DIR/nvm.sh" && npx playwright chromium --version || echo "Chromium installed"

# 创建浏览器清理脚本
RUN printf '#!/bin/bash\n\
# 清理 Playwright/Chrome 浏览器残留进程和锁文件\n\
pkill -9 -f "chromium" 2>/dev/null || true\n\
pkill -9 -f "chrome" 2>/dev/null || true\n\
pkill -9 -f "mcp-server-playwright" 2>/dev/null || true\n\
# 清理锁文件和临时文件\n\
rm -f /tmp/.org.chromium.* 2>/dev/null\n\
rm -rf /tmp/playwright* 2>/dev/null\n\
rm -rf /tmp/.X* 2>/dev/null\n\
rm -rf /root/.cache/ms-playwright/.links/*.lock 2>/dev/null\n\
rm -rf /tmp/playwright-* 2>/dev/null\n\
echo "Browser cleanup completed"\n\
' > /usr/local/bin/cleanup-browser \
    && chmod +x /usr/local/bin/cleanup-browser

# 创建启动包装脚本 - 启动时自动清理浏览器
RUN printf '#!/bin/bash\n\
# 启动前清理浏览器残留\n\
/usr/local/bin/cleanup-browser\n\
# 启动 executor 服务\n\
exec python -m executor.main\n\
' > /usr/local/bin/start-executor \
    && chmod +x /usr/local/bin/start-executor

# =============================================================================
# 应用程序安装
# =============================================================================
WORKDIR /app

# 复制 executor 代码（从项目根目录构建时的路径）
COPY backend/executor /app/executor

# 安装 Python 依赖
RUN pip install --no-cache-dir -r /app/executor/requirements.txt

# 创建工作区目录（将由 volume mount 覆盖）
RUN mkdir -p /workspace

# 设置 Python 路径
ENV PYTHONPATH=/app

# 沙箱模式标识
ENV IS_SANDBOX=1

# 保持工作目录为 /app（不要设置为 /workspace，因为 volume mount 可能在启动后才生效）
# Claude Code CLI 会在每次会话时切换到正确的工作目录

# =============================================================================
# Git 配置
# =============================================================================
RUN git config --global --add safe.directory '*'

# =============================================================================
# 端口暴露
# =============================================================================
# 8080: FastAPI executor 服务
# 3000: 预留给 repo 代码服务（由 repo 启动脚本管理）
EXPOSE 8080 3000

# =============================================================================
# 健康检查
# =============================================================================
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# =============================================================================
# 启动命令
# =============================================================================
# 使用启动包装脚本，启动前自动清理浏览器残留
CMD ["/usr/local/bin/start-executor"]

