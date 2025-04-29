import yaml


def load_data_config():
    with open('configs\data_configs.yml', "r") as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
    return config.get("table_columns", {})
