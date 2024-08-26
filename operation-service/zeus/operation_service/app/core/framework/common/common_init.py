def init_host_map(json_object, hosts_map):
    if "hosts" not in json_object.keys():
        return hosts_map
    hosts_map_tmp = {}
    hosts_list = json_object.get("hosts")
    for hostname in hosts_list:
        hosts_map_tmp[hostname] = hosts_map[hostname]
    return hosts_map_tmp


def init_dependency(json_object):
    if "dependency" not in json_object.keys():
        return []
    return json_object.get("dependency")
