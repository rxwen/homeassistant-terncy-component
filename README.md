# homeassistant-terncy-component
terncy custome component for homeassistant

[查看中文帮助](README.zh-cn.md)


[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)


## Component Information

- ha_iot_class: Local Push
- ha_release: '2022.7.0'
- ha_config_flow: true
- ha_domain: terncy

The Terncy integration allows you to control your Terncy devices connected to the Terncy Home Center (a Zigbee gateway) with Home Assistant.

There is support for the following device type within Home Assistant:

- Light
- Switch
- Curtain Motor
- Wireless Switch
- Smart Plug
- Smart Dial (Button press event only)
- Motion Sensor
- Door Sensor
- Temperature Sensor
- Humidity Sensor
- Illuminance Sensor
- Air Conditioner

## Manul Installation

1. Download component from [Releases](https://github.com/rxwen/homeassistant-terncy-component/releases)
1. Extract the release to home assistant custom_components folder. Once installed, the file structure is like:
```
homeassistant_configuration_root
├── automations.yaml
├── blueprints
├── configuration.yaml
├── custom_components
│   └── terncy
│       ├── translations
│       ├── __init__.py
│       ├── binary_sensor.py
│       ├── config_flow.py
│       ├── const.py
│       ├── cover.py
│       ├── ...
```
3. Restart home assistant

## Installation via [HACS](https://hacs.xyz/)

- [Install hacs](https://hacs.xyz/docs/setup/download) for the HA.
- Go to HACS page in your HA.
- Click the triple dot icon in the top right corner, then select Custom repositories.
- Input `https://github.com/rxwen/homeassistant-terncy-component` in the Repository, and select Integration in the Category. Then click Add.
- Go to Integration page in HACS, click the Add button in the bottom right corner.
- Input "terncy" to search for Terncy component and click the search result to view detail.
- Click the Download button in the bottom right corner to view download details.
- Select the most recent verion and Download the component.
- Restart HA.

## Installation with git and docker/podman

- Git clone current project to a local direcoty
- `docker pull homeassistant/home-assistant:stable`
- `docker run -it --rm --name ha --network=host -v PATH_TO_LOCAL_CLONED_GIT_REPOSITORY:/config/ homeassistant/home-assistant:stable`

## Configuration

The Terncy integration is automatically discovered. Or add it via the add integration menu.

Before trying to control Terncy devices through Home Assistant, you have to set up the system using the [Terncy app](https://www.terncy.com/app/).

- To set up this integration, click Configuration in the sidebar and then click Integrations. You should see "Terncy" in the discovered section (if you do not, click the + icon in the lower right and find Terncy). 
- Click configure and you will be presented with the initiation dialog. This will prompt you to select the Terncy Home Center to connect.
- After you click submit, you will get an access request in Terncy app. Within Terncy app, You'll find the pending access request in Home Center configuraiton page, under Local Access menu entry.
- After you approved the access, click submit to finish adding Terncy.

Once registration is complete you should see the Terncy lights listed as light entities.

## Debugging

Enable and view log of Terncy component

Edit configuration.yaml file in home assistant config directory, add below contents:

```
default_config:

logger:
  default: warning
  logs:
    custom_components.terncy: debug

```

View log at http://{ip_of_home_assistant}:8123/config/logs, or with  `docker logs -f --tail 0  {docker_instantce_name}` if running home assistant in docker.

## Note

- When running ha in docker, the docker should be in [host network mode](https://docs.docker.com/network/host/), by appending `--netwrok host` argument to docker start command.
