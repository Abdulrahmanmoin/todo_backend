import pkg_resources
try:
    installed_packages = pkg_resources.working_set
    for i in installed_packages:
        if 'openai' in i.key or 'agent' in i.key:
            print(f"{i.key}=={i.version}")
except Exception as e:
    print(e)
