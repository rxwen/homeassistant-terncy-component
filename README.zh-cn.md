# homeassistant-terncy-component
小燕系统支持 Home Assistant 插件 [English](README.md)

## 插件信息

- ha_iot_class: Local Push
- home assistant 版本要求: '2021.3.1'
- ha_config_flow: true
- ha_domain: terncy

使用本插件可以在 Home Assistant 中控制小燕智能家居系统设备。

## 安装方法

1. 从 [Releases](https://github.com/rxwen/homeassistant-terncy-component/releases) 页下载插件最新版本
1. 将插件解压安装到 home assistant 配置目录下的 custom_components 目录中。安装后，目录结构如下：
```
homeassistant_configuration_root
├── automations.yaml
├── blueprints
├── configuration.yaml
├── custom_components
│   └── terncy
│       ├── config_flow.py
│       ├── const.py
| ...
```
3. 重启 home assistant


## 配置流程

插件安装完成后，home assistant 可以自动发现网络中的小燕家庭中心。

连接小燕设备之前，请先使用[小燕在家](https://www.xiaoyan.io/app) App 完成系统配置。

- 在 home assistant 的页面上，点击自动发现的小燕家庭中心图标的配置按钮，启动初始化流程。
- 在弹出窗口点击提交。
- 此时在小燕在家 App 中可收到 home assistant 请求连接的提醒，点击同意。（如未发现提示框，请查看家庭中心配置页，进入局域网访问授权栏查看）
- 回到 home assistant 页面再次点击提交，完成配置

配置完成后，即可在 home assistant 中看到小燕设备。

## 调试

启用及查看小燕插件日志的方法

在 home assistant 配置目录下的 configuration.yaml 文件中添加以下内容：

```
default_config:

logger:
  default: info
  logs:
    homeassistant.components.terncy: info

```

重启 home assistant 后，可在 http://{ip_of_home_assistant}:8123/config/logs 页查看日志。如果通过 docker 运行 home assistant，也可用 `docker logs -f --tail 0  {docker_instantce_name}` 命令查看。

