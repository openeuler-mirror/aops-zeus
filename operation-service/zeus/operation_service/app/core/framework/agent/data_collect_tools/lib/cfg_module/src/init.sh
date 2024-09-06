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


#########################################################
# Function name:     Atae_cfg_init
# Description:       Initialization module
# Input parameter:   $1=The path of cfg_module
# Output parameter:  NA
# Return value:      If the response is successful, 0 is returned. 
#                    If the operation fails, an error code is returned
#########################################################
function Atae_cfg_init()
{
    function log()
    {
        local log_level=""
        local message=""

        if [ $# -gt 1 ] ; then
            log_level="$1"
            message="${@:2}"
        else
            log_level="INFO"
            message="${@}"
        fi
        
        message="[${log_level}]$(date '+%Y-%m-%d %H:%M:%S') ${HOSTNAME}[$$][${FUNCNAME[1]}:${BASH_LINENO[0]}]${message}"
        
        echo "${message}"
        
        return 0
    }
    
    local module_dir=$1
    local conf_dir=""
    local inner_dir=""
    local lib_dir=""
    local log_dir=""
    local customer_conf_file=""
    local inner_conf_file=""
    local lib_file=""
    local cfg_path=""
    local cfg_type="KV"
    
    if [ -n "${_ATAE_CFG_MODULE_VERSION_}" ] ; then
        log "Has init."
        return 0
    fi
    
    if [ -z "${module_dir}" ] ; then
        log "ERROR" "Para error!" >&2
        return 1
    fi
    
    if [ ! -d "${module_dir}" ] ; then
        log "ERROR" "Dir[${module_dir}] is not exist!" >&2
        return 1
    fi
    
    
    module_dir=$(readlink -m "${module_dir}")
    conf_dir="${module_dir}/conf"
    inner_dir="${module_dir}/inner"
    lib_dir="${module_dir}/lib"
    log_dir="${module_dir}/log"
    
    customer_conf_file="${conf_dir}/customer.conf"
    inner_conf_file="${inner_dir}/cfg.conf"
    lib_file="${lib_dir}/lib_cfg.sh"
    log_file="${log_dir}/cfg.log"
    

    
    if [ ! -f "${lib_file}" ] ; then
        log "ERROR" "File[${lib_file}] is not exist!" >&2
        return 1
    fi
    
    [ ! -d "${conf_dir}" ] && mkdir -p "${conf_dir}"
    [ ! -d "${inner_dir}" ] && mkdir -p "${inner_dir}"
    [ ! -d "${log_dir}" ] && mkdir -p "${log_dir}"
    [ ! -f "${customer_conf_file}" ] && touch "${customer_conf_file}"
    [ ! -f "${inner_conf_file}" ] && touch "${inner_conf_file}"
    [ ! -f "${log_file}" ] && touch "${log_file}"
    
    chmod 600 "${customer_conf_file}"
    chmod 600 "${inner_conf_file}"
    chmod 600 "${log_file}"
    
    source "${lib_file}"
    
    cfg_path="${customer_conf_file}"
    cfg_type="KV"
    _ATAE_CFG_MODULE_PATH_="${module_dir}"
    _ATAE_CFG_PATH_="${cfg_path}"
    _ATAE_CFG_TYPE_="${cfg_type}"
    _ATAE_CFG_LOG_FILE_="${log_file}"
    
    cfg_path=$(grep -E "^[[:space:]]*cfg_path[[:space:]]*=" "${inner_conf_file}" \
             | awk -F "^[[:space:]]*cfg_path[[:space:]]*=" '{print $2}' \
             | sed -r "s/^[[:space:]]*//g;s/[[:space:]]*$//g")
             
    if [ "${cfg_path}" != "${_ATAE_CFG_PATH_}" ] ; then
        if [ -f "${cfg_path}" ] ; then
            _ATAE_CFG_PATH_="${cfg_path}"
            chmod 600 "${log_file}"
            _atae_cfg_log_record_ "Config cfg_path=${_ATAE_CFG_PATH_}"
        else
            _atae_cfg_log_record_ "WARN" "File[${cfg_path}] been set in config[${inner_conf_file}] is not exist!"
            sed -i -r "/^[[:space:]]*cfg_path[[:space:]]*=/d" "${inner_conf_file}"
            echo "cfg_path=${_ATAE_CFG_PATH_}" >>"${inner_conf_file}"
            _atae_cfg_log_record_ "Re-config cfg_path=${_ATAE_CFG_PATH_}"
        fi
    else
        _atae_cfg_log_record_ "Default cfg_path=${_ATAE_CFG_PATH_}"
    fi
    
    cfg_type=$(grep -E "^[[:space:]]*cfg_type[[:space:]]*=" "${inner_conf_file}" \
             | awk -F "^[[:space:]]*cfg_type[[:space:]]*=" '{print $2}' \
             | sed -r "s/^[[:space:]]*//g;s/[[:space:]]*$//g")
             
    if [ "${cfg_type}" != "${_ATAE_CFG_TYPE_}" ] ; then
        if [ "${cfg_type}" == "KV" -o "${cfg_type}" == "Config" ] ; then
            _ATAE_CFG_TYPE_="${cfg_type}"
            _atae_cfg_log_record_ "Config cfg_type=${_ATAE_CFG_TYPE_}"
        else
            _atae_cfg_log_record_ "WARN" "Invalid cfg_type[${cfg_type}] in config[${inner_conf_file}]!"
            sed -i -r "/^[[:space:]]*cfg_type[[:space:]]*=/d" "${inner_conf_file}"
            echo "cfg_type=${_ATAE_CFG_TYPE_}" >>"${inner_conf_file}"
            _atae_cfg_log_record_ "Re-config cfg_type=${_ATAE_CFG_TYPE_}"
        fi
    else
        _atae_cfg_log_record_ "Default cfg_type=${_ATAE_CFG_TYPE_}"
    fi
    
    return 0
}