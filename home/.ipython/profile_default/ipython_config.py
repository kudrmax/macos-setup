c = get_config()  # noqa

# Отключаем jedi: из-за него ломается Tab-автодополнение в Jupyter/IPython
c.IPCompleter.use_jedi = False
