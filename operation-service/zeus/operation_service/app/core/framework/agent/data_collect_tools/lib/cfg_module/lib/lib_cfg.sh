#!/bin/bash
#########################################################
# Copyright (C), 2017-2019, Huawei Tech. Co., Ltd.
# File name: cfg.sh
# Author: 
# Version: 0.0.0.1 
# Date: 2017/9/18
# Description: conf_module module, which provides ini, conf, 
#              and other types of configuration access.
#########################################################

#Global variables
export _ATAE_CFG_MODULE_VERSION_="0.0.0.1"
export _ATAE_CFG_MODULE_PATH_=""
export _ATAE_CFG_LOG_FILE_=""
export _ATAE_CFG_PATH_=""
export _ATAE_CFG_TYPE_=""

#ATAE Error code
export ATAE_ERR_INVALIDPARAMETER=100             # Invalid parameter
export ATAE_ERR_MISSOBJECT=101                   # Specified object cannot be found
export ATAE_ERR_UNINIT=102                       # The module is not initialized
export ATAE_ERR_NOFIND=103                       # The directory or the file does not exist
export ATAE_ERR_NOPERMISSION=104                 # Permission denied
export ATAE_ERR_CONTENTERR=105                   # The configuration file content is incorrect
export ATAE_ERR_UNKNOW=106                      # The runtime unknown error
export ATAE_ERR_ERRTYPE=107                     # Configure file type is incorrect

export python_cmd="python"
if [[ X"$(python3 --version)" != X"" ]]; then
    export python_cmd="python3"
fi
#模块内部函数。写指定LEVEL级别的日志，仅写文件
#入参：$1，日志级别，${@:2}是message 或 仅$1是message，日志级别将为INFO
#出参：无
function _atae_cfg_log_record_()
{
    declare -f atae_log_record >/dev/null
    if [ $? -eq 0 ] ; then
        atae_log_record "$@"
        return $?
    fi
    
    local log_level=""
    local message=""
    
    if [ ! -f "${_ATAE_CFG_LOG_FILE_}" ] ; then
        return 1
    fi
    
    if [ $# -gt 1 ] ; then
        log_level="$1"
        message="${@:2}"
    else
        log_level="INFO"
        message="${@}"
    fi

    if [ "${log_level}" != "DEBUG" -a "${log_level}" != "INFO" -a "${log_level}" != "WARN" -a "${log_level}" != "ERROR" ] ; then
        log_level="INFO"
    fi
    
    message="[${log_level}]$(date '+%Y-%m-%d %H:%M:%S') ${HOSTNAME}[$$][${FUNCNAME[1]}:${BASH_LINENO[0]}]${message}"
    echo "${message}" >>"${_ATAE_CFG_LOG_FILE_}"
    
    return 0
}
export -f _atae_cfg_log_record_

#########################################################
# Function name:     atae_cfg_set_path
# Description:       Set the configuration file path
# Input parameter:   $1=the value of atae_cfg_path
# Output parameter:  NA
# Return value:      If the response is successful, 0 is returned. 
#                    If the operation fails, an error code is returned
#########################################################
function atae_cfg_set_path()
{
    local cfg_path=$1
    
    if [ ! -f "${cfg_path}" ] ; then
        _atae_cfg_log_record_ "ERROR" "File[${cfg_path}] is not exist"
        return 1
    fi
    
    if [ "${cfg_path}" == "${_ATAE_CFG_PATH_}" ] ; then
        _atae_cfg_log_record_ "DEBUG" "cfg_path[${cfg_path}] no change."
        return 0
    fi
    
    _atae_cfg_log_record_ "DEBUG" "New cfg_path=${cfg_path}"
    chmod 600 "${cfg_path}"
    _ATAE_CFG_PATH_="${cfg_path}"
    
    return 0
}
export -f atae_cfg_set_path

#########################################################
# Function name:     atae_cfg_get_path
# Description:       Get the configuration file path
# Input parameter:   NA
# Output parameter:  the value of atae_cfg_path
# Return value:      If the response is successful, 0 is returned. 
#                    If the operation fails, an error code is returned
#########################################################
function atae_cfg_get_path()
{
    echo "${_ATAE_CFG_PATH_}"
    return 0
}
export -f atae_cfg_get_path

#########################################################
# Function name:     atae_cfg_set_type
# Description:       Set the format of the configuration file type. KV or Config. The name is case sensitive.
# Input parameter:   $1=the value of atae_cfg_type
# Output parameter:  NA
# Return value:      If the response is successful, 0 is returned. 
#                    If the operation fails, an error code is returned
#########################################################
function atae_cfg_set_type()
{
    local cfg_type=$1
    
    if [ "${cfg_type}" == "KV" -o "${cfg_type}" == "Config" ] ; then
        if [ "${cfg_type}" == "${_ATAE_CFG_TYPE_}" ] ; then
            _atae_cfg_log_record_ "DEBUG" "cfg_type[${cfg_type}] no change."
            return 0
        fi
        
        _atae_cfg_log_record_ "DEBUG" "New cfg_type=${cfg_type}, old cfg_type=${_ATAE_CFG_TYPE_}"
        _ATAE_CFG_TYPE_="${cfg_type}"
        return 0
    fi
    
    _atae_cfg_log_record_ "ERROR" "Invalid cfg_type[${cfg_type}]"
    return 1
}
export -f atae_cfg_set_type

#########################################################
# Function name:     atae_cfg_get_type
# Description:       Get the format of the configuration file type
# Input parameter:   NA
# Output parameter:  the value of atae_cfg_type
# Return value:      If the response is successful, 0 is returned. 
#                    If the operation fails, an error code is returned
#########################################################
function atae_cfg_get_type()
{
    echo "${_ATAE_CFG_TYPE_}"
    return 0
}
export -f atae_cfg_get_type

#########################################################
# Function name:     atae_cfg_save
# Description:       Save the set to the module configuration file
# Input parameter:   NA
# Output parameter:  NA
# Return value:      If the response is successful, 0 is returned. 
#                    If the operation fails, an error code is returned
#########################################################
function atae_cfg_save()
{
    local inner_conf_file="${_ATAE_CFG_MODULE_PATH_}/inner/cfg.conf"
    
    if [ ! -d "${_ATAE_CFG_MODULE_PATH_}" ] ; then
        _atae_cfg_log_record_ "ERROR" "Please init the module."
        return 1
    fi
    
    if [ ! -f "${inner_conf_file}" ] ; then
        mkdir -p "$(dirname "${inner_conf_file}")"
        touch "${inner_conf_file}"
        chmod 600 "${inner_conf_file}"
    fi
    
    if [ -n "${_ATAE_CFG_PATH_}" ] ; then
        sed -i -r "/^[[:space:]]*cfg_path[[:space:]]*=/d" "${inner_conf_file}"
        echo "cfg_path=${_ATAE_CFG_PATH_}" >>"${inner_conf_file}"
    fi
    
    if [ -n "${_ATAE_CFG_TYPE_}" ] ; then
        sed -i -r "/^[[:space:]]*cfg_type[[:space:]]*=/d" "${inner_conf_file}"
        echo "cfg_type=${_ATAE_CFG_TYPE_}" >>"${inner_conf_file}"
    fi
    
    return 0
}
export -f atae_cfg_save

#########################################################
# Function name:     atae_cfg_get_keys
# Description:       get all keys
# Input parameter:   NA
# Output parameter:  Standard output
# Return value:      If the response is successful, 0 is returned. 
#                    If the operation fails, an error code is returned
#########################################################
function atae_cfg_get_keys()
{
    local conf_file="${_ATAE_CFG_PATH_}"
    
    if [ "${_ATAE_CFG_TYPE_}" != "KV" ] ; then
        _atae_cfg_log_record_ "ERROR" "The cfg_type[${_ATAE_CFG_TYPE_}] must be KV"
        return $ATAE_ERR_ERRTYPE
    fi
    
    if [ ! -f "${conf_file}" ] ; then
        _atae_cfg_log_record_ "ERROR" "File conf_file[${conf_file}] not exist"
        return $ATAE_ERR_ERRTYPE
    fi
    
    grep -E "^[[:space:]]*[^#]+[[:space:]]*=" "${conf_file}" \
        | grep -E -v "^[[:space:]]*#" \
        | awk -F "=" '{print $1}' \
        | sed -r "s/^[[:space:]]*//g;s/[[:space:]]*$//g;/^[[:space:]]*$/d"
    return 0
}
export -f atae_cfg_get_keys

#########################################################
# Function name:     atae_cfg_get_key_value
# Description:       The configuration file to obtain all key
# Input parameter:   $1=key
# Output parameter:  Standard output
# Return value:      If the response is successful, 0 is returned. 
#                    If the operation fails, an error code is returned
#########################################################
function atae_cfg_get_key_value()
{
    local key=$1
    local key_num=0
    local conf_file="${_ATAE_CFG_PATH_}"
    
    if [ "${_ATAE_CFG_TYPE_}" != "KV" ] ; then
        _atae_cfg_log_record_ "ERROR" "The cfg_type[${_ATAE_CFG_TYPE_}] must be KV"
        return $ATAE_ERR_ERRTYPE
    fi
    
    if [ ! -f "${conf_file}" ] ; then
        _atae_cfg_log_record_ "ERROR" "File conf_file[${conf_file}] not exist"
        return $ATAE_ERR_ERRTYPE
    fi
    
    if [ -z "${key}" ] || [[ "${key}" =~ ^[[:space:]]*# ]] || [[ "${key}" =~ ^[[:space:]]*$ ]] ; then
        _atae_cfg_log_record_ "ERROR" "Invalid key[${key}]"
        return $ATAE_ERR_INVALIDPARAMETER
    fi

    key_num=$(grep -E "^[[:space:]]*${key}[[:space:]]*=" "${conf_file}" | wc -l)
    if [ "${key_num}" -eq 1 ] ; then
        grep -E "^[[:space:]]*${key}[[:space:]]*=" "${conf_file}" \
        | awk -F "^[[:space:]]*${key}[[:space:]]*=" '{print $2}' \
        | sed -r "s/^[[:space:]]*//g;s/[[:space:]]*$//g"
    elif [ "${key_num}" -gt 1 ];then
        _atae_cfg_log_record_ "ERROR" "The key[${key}] is more than one in config[${conf_file}]."
        return $ATAE_ERR_CONTENTERR
    fi
    
    return 0
}
export -f atae_cfg_get_key_value

#########################################################
# Function name:     atae_cfg_set_key_value
# Description:       The configuration file and set the key value.If the atae_cfg_type is not KV, the error message is returned.
# Input parameter:   $1=key
#                    $2=value
# Output parameter:  NA
# Return value:      If the response is successful, 0 is returned. 
#                    If the operation fails, an error code is returned
#########################################################
function atae_cfg_set_key_value()
{
    local key=$1
    local value=$2
    local key_num=0
    local conf_file="${_ATAE_CFG_PATH_}"
    
    if [ "${_ATAE_CFG_TYPE_}" != "KV" ] ; then
        _atae_cfg_log_record_ "ERROR" "The cfg_type[${_ATAE_CFG_TYPE_}] must be KV"
        return $ATAE_ERR_ERRTYPE
    fi
    
    if [ ! -f "${conf_file}" ] ; then
        _atae_cfg_log_record_ "ERROR" "File cfg_path[${conf_file}] not exist"
        return $ATAE_ERR_ERRTYPE
    fi
    
    if [ -z "${key}" ] || [[ "${key}" =~ ^[[:space:]]*# ]] || [[ "${key}" =~ ^[[:space:]]*$ ]] ; then
        _atae_cfg_log_record_ "ERROR" "Invalid key[${key}]"
        return $ATAE_ERR_INVALIDPARAMETER
    fi

    key_num=$(grep -E "^[[:space:]]*${key}[[:space:]]*=" "${conf_file}" | wc -l)
    if [ "${key_num}" -eq 1 ] ; then
        sed -i -r "/^[[:space:]]*${key}[[:space:]]*=/c ${key}=${value}" "${conf_file}"
    elif [ "${key_num}" -eq 0 ] ; then
        echo "${key}=${value}" >>"${conf_file}"
    elif [ "${key_num}" -gt 1 ];then
        _atae_cfg_log_record_ "ERROR" "The key[${key}] is more than one in config[${conf_file}]."
        return $ATAE_ERR_CONTENTERR
    fi
    return 0
}
export -f atae_cfg_set_key_value

#########################################################
# Function name:     atae_cfg_get_sections
# Description:       get all sections 
# Input parameter:   NA
# Output parameter:  Standard output
# Return value:      If the response is successful, 0 is returned. 
#                    If the operation fails, an error code is returned
#########################################################
function atae_cfg_get_sections()
{
    local cmd_value=""
    local ret=0
    local conf_file="${_ATAE_CFG_PATH_}"
    
    if [ "${_ATAE_CFG_TYPE_}" != "Config" ] ; then
        _atae_cfg_log_record_ "ERROR" "The cfg_type[${_ATAE_CFG_TYPE_}] must be Config"
        return $ATAE_ERR_ERRTYPE
    fi
    
    if [ ! -f "${conf_file}" ] ; then
        _atae_cfg_log_record_ "ERROR" "File conf_file[${conf_file}] not exist"
        return $ATAE_ERR_ERRTYPE
    fi
    cmd_value=$(${python_cmd} -c "
try:
    import os, sys
    if sys.version_info.major == 2:
        import ConfigParser
        config = ConfigParser.ConfigParser()
    elif sys.version_info.major == 3:
        import configparser
        config = configparser.ConfigParser()
    else:
        raise Exception('''python version error''')

    config.optionxform = lambda option: option
    config.read('''${conf_file}''')
    print ('%s' % '\n'.join(config.sections()))
    sys.exit(0)
except Exception as e:
    print(e)
    sys.exit(1)
" 2>&1
)
    ret=$?
    if [ "${ret}" -eq 0 ] ; then
        echo -e "${cmd_value}"
        return 0
    fi
    
    _atae_cfg_log_record_ "ERROR" "Call python failed:${cmd_value}"
    return $ATAE_ERR_CONTENTERR
}
export -f atae_cfg_get_sections

#########################################################
# Function name:     atae_cfg_get_section_keys
# Description:       get all key of section
# Input parameter:   $1=section
# Output parameter:  Standard output
# Return value:      If the response is successful, 0 is returned. 
#                    If the operation fails, an error code is returned
#########################################################
function atae_cfg_get_section_keys()
{
    local section=$1
    local cmd_value=""
    local ret=0
    local conf_file="${_ATAE_CFG_PATH_}"
    
    if [ "${_ATAE_CFG_TYPE_}" != "Config" ] ; then
        _atae_cfg_log_record_ "ERROR" "The cfg_type[${_ATAE_CFG_TYPE_}] must be Config"
        return $ATAE_ERR_ERRTYPE
    fi
    
    if [ ! -f "${conf_file}" ] ; then
        _atae_cfg_log_record_ "ERROR" "File cfg_path[${conf_file}] not exist"
        return $ATAE_ERR_ERRTYPE
    fi
    
    if [ -z "${section}" ] || [[ "${section}" =~ ^[[:space:]]*# ]] || [[ "${section}" =~ ^[[:space:]]*$ ]] ; then
        _atae_cfg_log_record_ "ERROR" "Invalid section[${section}]"
        return $ATAE_ERR_INVALIDPARAMETER
    fi
    cmd_value=$(${python_cmd} -c "
try:
    import os, sys
    if sys.version_info.major == 2:
        import ConfigParser
        config = ConfigParser.ConfigParser()
    elif sys.version_info.major == 3:
        import configparser
        config = configparser.ConfigParser()
    else:
        raise Exception('''python version error''')
    
    config.optionxform = lambda option: option
    config.read('''${conf_file}''')
    if True != config.has_section('''${section}'''):
        print ('''No has section[${section}]''')
        sys.exit(1)
    if len(config.options('''${section}''')):
        print ('%s' % '\n'.join(config.options('''${section}''')))
    sys.exit(0)
except Exception as e:
    print(e)
    sys.exit(1)
" 2>&1
)
    ret=$?
    if [ "${ret}" -eq 0 ] ; then
        echo -e "${cmd_value}"
        return 0
    fi
    
    _atae_cfg_log_record_ "ERROR" "Call python failed:${cmd_value}"
    return $ATAE_ERR_CONTENTERR
}
export -f atae_cfg_get_section_keys

#########################################################
# Function name:     atae_cfg_get_section_key_value
# Description:       get key's value of section
# Input parameter:   $1=section
#                    $2=key
# Output parameter:  Standard output
# Return value:      If the response is successful, 0 is returned. 
#                    If the operation fails, an error code is returned
#########################################################
function atae_cfg_get_section_key_value()
{
    local section=$1
    local keyname=$2
    local cmd_value=""
    local ret=0
    local conf_file="${_ATAE_CFG_PATH_}"
    
    if [ "${_ATAE_CFG_TYPE_}" != "Config" ] ; then
        _atae_cfg_log_record_ "ERROR" "The cfg_type[${_ATAE_CFG_TYPE_}] must be Config"
        return $ATAE_ERR_ERRTYPE
    fi
    
    if [ ! -f "${conf_file}" ] ; then
        _atae_cfg_log_record_ "ERROR" "File conf_file[${conf_file}] not exist"
        return $ATAE_ERR_ERRTYPE
    fi
    
    if [ -z "${section}" ] || [[ "${section}" =~ ^[[:space:]]*# ]] || [[ "${section}" =~ ^[[:space:]]*$ ]] ; then
        _atae_cfg_log_record_ "ERROR" "Invalid section[${section}]"
        return $ATAE_ERR_INVALIDPARAMETER
    fi
    
    if [ -z "${keyname}" ] || [[ "${keyname}" =~ ^[[:space:]]*# ]] || [[ "${keyname}" =~ ^[[:space:]]*$ ]] ; then
        _atae_cfg_log_record_ "ERROR" "Invalid keyname[${keyname}]"
        return $ATAE_ERR_INVALIDPARAMETER
    fi
    cmd_value=$(${python_cmd} -c "
try:
    import os, sys
    if sys.version_info.major == 2:
        import ConfigParser
        config = ConfigParser.ConfigParser()
    elif sys.version_info.major == 3:
        import configparser
        config = configparser.ConfigParser()
    else:
        raise Exception('''python version error''')
    
    config.optionxform = lambda option: option
    config.read('''${conf_file}''')
    if True != config.has_section('''${section}'''):
        print ('''No has section[${section}]''')
        sys.exit(1)
    if True != config.has_option('''${section}''', '''${keyname}'''):
        print ('''No has option[${keyname}]''')
        sys.exit(1)
    value = config.get('''${section}''', '''${keyname}''')
    if len(value):
        print ('%s' % value)
    sys.exit(0)
except Exception as e:
    print(e)
    sys.exit(1)
" 2>&1
)
    ret=$?
    if [ "${ret}" -eq 0 ] ; then
        echo -e "${cmd_value}"
        return 0
    fi
    
    _atae_cfg_log_record_ "ERROR" "Call python failed:${cmd_value}"
    return $ATAE_ERR_CONTENTERR
}
export -f atae_cfg_get_section_key_value

#########################################################
# Function name:     atae_cfg_set_section_key_value
# Description:       set key's value of section,If the section does not exist, 
#                    run the following command to create. If the key does not exist, this command is used to add the parameter.
# Input parameter:   $1=section
#                    $2=key
#                    $3=value
# Output parameter:  NA
# Return value:      If the response is successful, 0 is returned. 
#                    If the operation fails, an error code is returned
#########################################################
function atae_cfg_set_section_key_value()
{
    local section=$1
    local keyname=$2
    local value=$3
    local cmd_value=""
    local ret=0
    local conf_file="${_ATAE_CFG_PATH_}"
    
    if [ "${_ATAE_CFG_TYPE_}" != "Config" ] ; then
        _atae_cfg_log_record_ "ERROR" "The cfg_type[${_ATAE_CFG_TYPE_}] must be Config"
        return $ATAE_ERR_ERRTYPE
    fi
    
    if [ ! -f "${conf_file}" ] ; then
        _atae_cfg_log_record_ "ERROR" "File conf_file[${conf_file}] not exist"
        return $ATAE_ERR_ERRTYPE
    fi
    
    if [ -z "${section}" ] || [[ "${section}" =~ ^[[:space:]]*# ]] || [[ "${section}" =~ ^[[:space:]]*$ ]] ; then
        _atae_cfg_log_record_ "ERROR" "Invalid section[${section}]"
        return $ATAE_ERR_INVALIDPARAMETER
    fi
    
    if [ -z "${keyname}" ] || [[ "${keyname}" =~ ^[[:space:]]*# ]] || [[ "${keyname}" =~ ^[[:space:]]*$ ]] ; then
        _atae_cfg_log_record_ "ERROR" "Invalid keyname[${keyname}]"
        return $ATAE_ERR_INVALIDPARAMETER
    fi
    cmd_value=$(${python_cmd} -c "
try:
    import os, sys
    if sys.version_info.major == 2:
        import ConfigParser
        config = ConfigParser.ConfigParser()
    elif sys.version_info.major == 3:
        import configparser
        config = configparser.ConfigParser()
    else:
        raise Exception('''python version error''')
    
    config.optionxform = lambda option: option
    config.read('''${conf_file}''')
    if True != config.has_section('''${section}'''):
        config.add_section('''$section''')
    config.set('''${section}''', '''${keyname}''', '''${value}''')
    with open('''${conf_file}''', 'w+') as configfile:
        config.write(configfile)
    sys.exit(0)
except Exception as e:
    print(e)
    sys.exit(1)
" 2>&1
)
    ret=$?
    if [ "${ret}" -eq 0 ] ; then
        return 0
    fi
    
    _atae_cfg_log_record_ "ERROR" "Call python failed:${cmd_value}"
    return $ATAE_ERR_CONTENTERR
}
export -f atae_cfg_set_section_key_value


#########################################################
# Function name:     atae_cfg_get_keys
# Description:       get all keys
# Input parameter:   NA
# Output parameter:  Standard output
# Return value:      If the response is successful, 0 is returned. 
#                    If the operation fails, an error code is returned
#########################################################
function atae_cfg_get_file_keys()
{
    local conf_file=$1
    
    if [ ! -f "${conf_file}" ] ; then
        _atae_cfg_log_record_ "ERROR" "File conf_file[${conf_file}] not exist"
        return $ATAE_ERR_ERRTYPE
    fi
    
    grep -E "^[[:space:]]*[^#]+[[:space:]]*=" "${conf_file}" \
        | grep -E -v "^[[:space:]]*#" \
        | awk -F "=" '{print $1}' \
        | sed -r "s/^[[:space:]]*//g;s/[[:space:]]*$//g;/^[[:space:]]*$/d"
    return 0
}
export -f atae_cfg_get_file_keys

#########################################################
# Function name:     atae_cfg_get_key_value
# Description:       The configuration file to obtain all key
# Input parameter:   $1=key
# Output parameter:  Standard output
# Return value:      If the response is successful, 0 is returned. 
#                    If the operation fails, an error code is returned
#########################################################
function atae_cfg_get_file_key_value()
{
    local conf_file=$1
    local key=$2
    local key_num=0
    
    if [ ! -f "${conf_file}" ] ; then
        _atae_cfg_log_record_ "ERROR" "File conf_file[${conf_file}] not exist"
        return $ATAE_ERR_ERRTYPE
    fi
    
    if [ -z "${key}" ] || [[ "${key}" =~ ^[[:space:]]*# ]] || [[ "${key}" =~ ^[[:space:]]*$ ]] ; then
        _atae_cfg_log_record_ "ERROR" "Invalid key[${key}]"
        return $ATAE_ERR_INVALIDPARAMETER
    fi

    key_num=$(grep -E "^[[:space:]]*${key}[[:space:]]*=" "${conf_file}" | wc -l)
    if [ "${key_num}" -eq 1 ] ; then
        grep -E "^[[:space:]]*${key}[[:space:]]*=" "${conf_file}" \
        | awk -F "^[[:space:]]*${key}[[:space:]]*=" '{print $2}' \
        | sed -r "s/^[[:space:]]*//g;s/[[:space:]]*$//g"
    elif [ "${key_num}" -gt 1 ];then
        _atae_cfg_log_record_ "ERROR" "The key[${key}] is more than one in config[${conf_file}]."
        return $ATAE_ERR_CONTENTERR
    fi
    
    return 0
}
export -f atae_cfg_get_file_key_value

#########################################################
# Function name:     atae_cfg_set_key_value
# Description:       The configuration file and set the key value.If the atae_cfg_type is not KV, the error message is returned.
# Input parameter:   $1=key
#                    $2=value
# Output parameter:  NA
# Return value:      If the response is successful, 0 is returned. 
#                    If the operation fails, an error code is returned
#########################################################
function atae_cfg_set_file_key_value()
{
    local conf_file=$1
    local key=$2
    local value=$3
    local key_num=0
    
    if [ ! -f "${conf_file}" ] ; then
        _atae_cfg_log_record_ "ERROR" "File conf_file[${conf_file}] not exist"
        return $ATAE_ERR_ERRTYPE
    fi
    
    if [ -z "${key}" ] || [[ "${key}" =~ ^[[:space:]]*# ]] || [[ "${key}" =~ ^[[:space:]]*$ ]] ; then
        _atae_cfg_log_record_ "ERROR" "Invalid key[${key}]"
        return $ATAE_ERR_INVALIDPARAMETER
    fi

    key_num=$(grep -E "^[[:space:]]*${key}[[:space:]]*=" "${conf_file}" | wc -l)
    if [ "${key_num}" -eq 1 ] ; then
        sed -i -r "/^[[:space:]]*${key}[[:space:]]*=/c ${key}=${value}" "${conf_file}"
    elif [ "${key_num}" -eq 0 ] ; then
        echo "${key}=${value}" >>"${conf_file}"
    elif [ "${key_num}" -gt 1 ];then
        _atae_cfg_log_record_ "ERROR" "The key[${key}] is more than one in config[${conf_file}]."
        return $ATAE_ERR_CONTENTERR
    fi
    return 0
}
export -f atae_cfg_set_file_key_value

#########################################################
# Function name:     atae_cfg_get_sections
# Description:       get all sections 
# Input parameter:   NA
# Output parameter:  Standard output
# Return value:      If the response is successful, 0 is returned. 
#                    If the operation fails, an error code is returned
#########################################################
function atae_cfg_get_file_sections()
{
    local conf_file=$1
    local cmd_value=""
    local ret=0
    
    if [ ! -f "${conf_file}" ] ; then
        _atae_cfg_log_record_ "ERROR" "File conf_file[${conf_file}] not exist"
        return $ATAE_ERR_ERRTYPE
    fi
    cmd_value=$(${python_cmd} -c "
try:
    import os, sys
    if sys.version_info.major == 2:
        import ConfigParser
        config = ConfigParser.ConfigParser()
    elif sys.version_info.major == 3:
        import configparser
        config = configparser.ConfigParser()
    else:
        raise Exception('''python version error''')
    
    config.optionxform = lambda option: option
    config.read('''${conf_file}''')
    print ('%s' % '\n'.join(config.sections()))
    sys.exit(0)
except Exception as e:
    print(e)
    sys.exit(1)
" 2>&1
)
    ret=$?
    if [ "${ret}" -eq 0 ] ; then
        echo -e "${cmd_value}"
        return 0
    fi
    
    _atae_cfg_log_record_ "ERROR" "Call python failed:${cmd_value}"
    return $ATAE_ERR_CONTENTERR
}
export -f atae_cfg_get_file_sections

#########################################################
# Function name:     atae_cfg_get_section_keys
# Description:       get all key of section
# Input parameter:   $1=section
# Output parameter:  Standard output
# Return value:      If the response is successful, 0 is returned. 
#                    If the operation fails, an error code is returned
#########################################################
function atae_cfg_get_file_section_keys()
{
    local conf_file=$1
    local section=$2
    local cmd_value=""
    local ret=0
    
    if [ ! -f "${conf_file}" ] ; then
        _atae_cfg_log_record_ "ERROR" "File conf_file[${conf_file}] not exist"
        return $ATAE_ERR_ERRTYPE
    fi
    
    if [ -z "${section}" ] || [[ "${section}" =~ ^[[:space:]]*# ]] || [[ "${section}" =~ ^[[:space:]]*$ ]] ; then
        _atae_cfg_log_record_ "ERROR" "Invalid section[${section}]"
        return $ATAE_ERR_INVALIDPARAMETER
    fi
    cmd_value=$(${python_cmd} -c "
try:
    import os, sys
    if sys.version_info.major == 2:
        import ConfigParser
        config = ConfigParser.ConfigParser()
    elif sys.version_info.major == 3:
        import configparser
        config = configparser.ConfigParser()
    else:
        raise Exception('''python version error''')
    
    config=ConfigParser.ConfigParser()
    config.optionxform = lambda option: option
    config.read('''${conf_file}''')
    if True != config.has_section('''${section}'''):
        print ('''No has section[${section}]''')
        sys.exit(1)
    if len(config.options('''${section}''')):
        print ('%s' % '\n'.join(config.options('''${section}''')))
    sys.exit(0)
except Exception as e:
    print(e)
    sys.exit(1)
" 2>&1
)
    ret=$?
    if [ "${ret}" -eq 0 ] ; then
        echo -e "${cmd_value}"
        return 0
    fi
    
    _atae_cfg_log_record_ "ERROR" "Call python failed:${cmd_value}"
    return $ATAE_ERR_CONTENTERR
}
export -f atae_cfg_get_file_section_keys

#########################################################
# Function name:     atae_cfg_get_section_key_value
# Description:       get key's value of section
# Input parameter:   $1=section
#                    $2=key
# Output parameter:  Standard output
# Return value:      If the response is successful, 0 is returned. 
#                    If the operation fails, an error code is returned
#########################################################
function atae_cfg_get_file_section_key_value()
{
    local conf_file=$1
    local section=$2
    local keyname=$3
    local cmd_value=""
    local ret=0
    
    if [ ! -f "${conf_file}" ] ; then
        _atae_cfg_log_record_ "ERROR" "File conf_file[${conf_file}] not exist"
        return $ATAE_ERR_ERRTYPE
    fi
    
    if [ -z "${section}" ] || [[ "${section}" =~ ^[[:space:]]*# ]] || [[ "${section}" =~ ^[[:space:]]*$ ]] ; then
        _atae_cfg_log_record_ "ERROR" "Invalid section[${section}]"
        return $ATAE_ERR_INVALIDPARAMETER
    fi
    
    if [ -z "${keyname}" ] || [[ "${keyname}" =~ ^[[:space:]]*# ]] || [[ "${keyname}" =~ ^[[:space:]]*$ ]] ; then
        _atae_cfg_log_record_ "ERROR" "Invalid keyname[${keyname}]"
        return $ATAE_ERR_INVALIDPARAMETER
    fi
    cmd_value=$(${python_cmd} -c "
try:
    import os, sys
    if sys.version_info.major == 2:
        import ConfigParser
        config = ConfigParser.ConfigParser()
    elif sys.version_info.major == 3:
        import configparser
        config = configparser.ConfigParser()
    else:
        raise Exception('''python version error''')
    
    config.optionxform = lambda option: option
    config.read('''${conf_file}''')
    if True != config.has_section('''${section}''') or True != config.has_option('''${section}''', '''${keyname}'''):
        print ('''No has section[${section}]''')
        sys.exit(1)
    if True != config.has_option('''${section}''', '''${keyname}'''):
        print ('''No has option[${keyname}]''')
        sys.exit(1)
    value = config.get('''${section}''', '''${keyname}''')
    if len(value):
        print ('%s' % value)
    sys.exit(0)
except Exception as e:
    print(e)
    sys.exit(1)
" 2>&1
)
    ret=$?
    if [ "${ret}" -eq 0 ] ; then
        echo -e "${cmd_value}"
        return 0
    fi
    
    _atae_cfg_log_record_ "ERROR" "Call python failed:${cmd_value}"
    return $ATAE_ERR_CONTENTERR
}
export -f atae_cfg_get_file_section_key_value

#########################################################
# Function name:     atae_cfg_set_section_key_value
# Description:       set key's value of section,If the section does not exist, 
#                    run the following command to create. If the key does not exist, this command is used to add the parameter.
# Input parameter:   $1=section
#                    $2=key
#                    $3=value
# Output parameter:  NA
# Return value:      If the response is successful, 0 is returned. 
#                    If the operation fails, an error code is returned
#########################################################
function atae_cfg_set_file_section_key_value()
{
    local conf_file=$1
    local section=$2
    local keyname=$3
    local value=$4
    local cmd_value=""
    local ret=0
    
    if [ ! -f "${conf_file}" ] ; then
        _atae_cfg_log_record_ "ERROR" "File conf_file[${conf_file}] not exist"
        return $ATAE_ERR_ERRTYPE
    fi
    
    if [ -z "${section}" ] || [[ "${section}" =~ ^[[:space:]]*# ]] || [[ "${section}" =~ ^[[:space:]]*$ ]] ; then
        _atae_cfg_log_record_ "ERROR" "Invalid section[${section}]"
        return $ATAE_ERR_INVALIDPARAMETER
    fi
    
    if [ -z "${keyname}" ] || [[ "${keyname}" =~ ^[[:space:]]*# ]] || [[ "${keyname}" =~ ^[[:space:]]*$ ]] ; then
        _atae_cfg_log_record_ "ERROR" "Invalid keyname[${keyname}]"
        return $ATAE_ERR_INVALIDPARAMETER
    fi
    
    cmd_value=$(${python_cmd} -c "
try:
    import os, sys
    if sys.version_info.major == 2:
        import ConfigParser
        config = ConfigParser.ConfigParser()
    elif sys.version_info.major == 3:
        import configparser
        config = configparser.ConfigParser()
    else:
        raise Exception('''python version error''')
    
    config.optionxform = lambda option: option
    config.read('''${conf_file}''')
    if True != config.has_section('''${section}'''):
        config.add_section('''$section''')
    config.set('''${section}''', '''${keyname}''', '''${value}''')
    with open('''${conf_file}''', 'w+') as configfile:
        config.write(configfile)
    sys.exit(0)
except Exception as e:
    print(e)
    sys.exit(1)
" 2>&1
)
    ret=$?
    if [ "${ret}" -eq 0 ] ; then
        return 0
    fi
    
    _atae_cfg_log_record_ "ERROR" "Call python failed:${cmd_value}"
    return $ATAE_ERR_CONTENTERR
}
export -f atae_cfg_set_file_section_key_value


