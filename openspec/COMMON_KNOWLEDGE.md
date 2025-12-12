# 公共知识库 - 技术栈与开发规范

本文档用于记录项目中的公共技术栈信息、开发规范和约定，供PRD澄清和OpenSpec提案生成时使用。

---

## 技术栈 (Technology Stack)

### 后端 (Backend)

**核心技术框架：**
- **Java 8** - 基础编程语言
- **Spring Boot 2.3.2** - 应用框架
- **Spring Cloud Hoxton.SR9** - 微服务框架
- **Spring Cloud Alibaba 2.2.6.RELEASE** - 阿里云微服务组件
  - Nacos - 服务注册与配置中心

**数据持久化：**
- **数据库支持：** PostgreSQL, MySQL, Oracle, SQL Server（多数据库兼容）
- **实际部署数据库：** MySQL
- **ORM框架：** 
  - JPA (Java Persistence API)
  - MyBatis
  - MyBatis-Plus
- **JSON字段存储：** 使用MySQL的JSON类型或TEXT类型（待根据MySQL版本确定）

**中间件与服务：**
- **Redis** - 缓存服务（分布式缓存）
- **RabbitMQ** - 消息队列（微服务间异步通信）
- **MinIO** - 对象存储服务
- **Nacos** - 服务注册与配置中心（微服务核心组件）

**API文档：**
- **Swagger 2.9.2** - API文档生成工具

### 前端 (Frontend)

**核心框架：**
- **React 16.9.0** - UI框架（JavaScript，非TypeScript）
- **Ant Design 3.26.20** - UI组件库

**构建工具与包管理：**
- **Webpack** - 模块打包工具
- **Yarn** - 包管理器

**编程语言：**
- **JavaScript (ES6+)** - 当前项目使用JavaScript
- **TypeScript** - 可选支持，但当前项目不使用

**状态管理与路由：**
- **Redux** - 状态管理
  - redux-thunk - 异步action支持
- **React Router 4** - 路由管理

**可视化：**
- **ECharts** - 图表可视化库

**自定义组件：**
- **HVisions** - 自定义框架组件库

---

## 架构模式

### 微服务架构 ✅

**架构类型：** Spring Cloud微服务架构

**核心组件：**
- **Spring Cloud Hoxton.SR9** - 微服务框架
- **Spring Cloud Alibaba 2.2.6.RELEASE** - 阿里云微服务组件

**服务注册与发现：**
- **Nacos** - 服务注册中心和服务发现
  - 服务提供者注册到Nacos
  - 服务消费者从Nacos获取服务列表
  - 支持健康检查和故障转移

**配置管理：**
- **Nacos Config** - 分布式配置中心
  - 集中管理配置信息
  - 支持动态配置刷新
  - 支持多环境配置（dev/test/prod）

**服务间通信：**
- **Feign / OpenFeign** - 声明式HTTP客户端（推荐）
- **RestTemplate** - RESTful服务调用
- **RabbitMQ** - 异步消息通信（解耦服务）

**API网关：**
- **Spring Cloud Gateway** 或 **Zuul** - API网关（待确认具体使用哪个）
  - 统一入口
  - 路由转发
  - 负载均衡
  - 限流熔断

**负载均衡：**
- **Ribbon** - 客户端负载均衡
- **Nacos** - 服务发现与负载均衡

**熔断降级：**
- **Sentinel** 或 **Hystrix** - 服务容错（待确认具体使用哪个）
  - 服务熔断
  - 服务降级
  - 限流保护

**服务监控：**
- **Spring Boot Actuator** - 服务监控
- **Sleuth + Zipkin** - 分布式链路追踪（待确认）

**服务拆分原则：**
- 按业务领域拆分（如：问题管理服务、用户服务、审批服务等）
- 每个服务独立部署、独立数据库
- 服务间通过API或消息队列通信

**数据一致性：**
- 分布式事务：Seata（待确认）
- 最终一致性：通过消息队列保证

### 数据库多租户支持
- 支持PostgreSQL, MySQL, Oracle, SQL Server四种数据库
- ORM层需要兼容不同数据库的方言差异
- **实际部署使用：** MySQL
- **数据库隔离：** 每个微服务拥有独立数据库（数据库拆分）

---

## 部署环境

### 微服务部署要点
- 架构：Spring Cloud 微服务，每个服务独立部署，推荐容器化（Docker/K8s）
- 服务注册与配置：Nacos（建议高可用部署）
- 网关与流量：Gateway/Zuul + 负载均衡（Ribbon/Nacos）
- 中间件高可用：Redis、RabbitMQ、MinIO 可分别以集群/主从方式部署
- 数据库：各微服务独立库，当前实际使用 MySQL

---

## 第三方依赖

### 后端主要依赖
- Spring Boot 2.3.2
- Spring Cloud Hoxton.SR9
- Spring Cloud Alibaba 2.2.6.RELEASE
- MyBatis / MyBatis-Plus
- Redis客户端
- RabbitMQ客户端
- MinIO客户端
- Swagger 2.9.2

### 前端主要依赖
- React 16.9.0
- Ant Design 3.26.20
- Redux + redux-thunk
- React Router 4
- ECharts
- HVisions自定义组件
- Webpack（构建工具）
- Yarn（包管理器）

