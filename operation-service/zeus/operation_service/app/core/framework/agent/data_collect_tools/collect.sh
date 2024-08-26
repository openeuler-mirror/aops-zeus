#!/bin/bash
CUR_DIR=$(cd $(dirname $0) ; pwd)
UPLOAD_DIR=${UPLOAD_DIR-${CUR_DIR}}
LOG_PATH=${CUR_DIR}/data_collect
LOG_FILE=${LOG_PATH}/runlog.txt
LIB_PATH=${CUR_DIR}/lib
CONF_PATH=${CUR_DIR}/conf
ProductName=$(dmidecode | grep "Product Name:")
if [[ -f /etc/SuSE-release ]] ;then
    OS_NAME='SLES'
else
    OS_NAME=$(grep -w "NAME" /etc/os-release | awk -F= '{print $2}'| sed 's/"//g')
fi
source ${CUR_DIR}/common_lib.sh

###########################################################################
# Name: config_init                                                       #
# Usage: Loading the Configuration Parsing Module                         #
# Recommended Interface:                                                  #
#       1)atae_cfg_get_file_key_value [file] [key]                        #
#       2)atae_cfg_get_file_sections [file]                               #
#       3)atae_cfg_get_file_section_keys [file] [section]                 #
#       4)atae_cfg_get_file_section_key_value [file] [section] [key]      #
###########################################################################
function config_init()
{
    source "${LIB_PATH}"/cfg_module/src/init.sh >/dev/null 2>&1
    [[ $? -ne 0 ]] && echo "[ERROR]$(date '+%m-%d %H:%M:%S')[$$]: Failed to source config module, check whether ${LIB_PATH}/cfg_module/init.sh is existed." && return 1
    Atae_cfg_init "${LIB_PATH}"/cfg_module >/dev/null 2>&1
    [[ $? -ne 0 ]] && echo "[ERROR]$(date '+%m-%d %H:%M:%S')[$$]: Failed to init cfg_module!Check whether the ${LIB_PATH}/log_module is complete." && return 1
    atae_cfg_set_type "Config" >/dev/null 2>&1
    atae_cfg_save >/dev/null 2>&1
    return 0
}


function collector_dir()
{
    local conf_file=$1
    local section=$2
    local output=$3
    local os_scope=$(atae_cfg_get_file_section_key_value ${conf_file} ${section} "os_scope")
    [[ ${os_scope} != 'common' && ${OS_NAME} != ${os_scope} ]] && return 0
    local format=$(atae_cfg_get_file_section_key_value ${conf_file} ${section} "format")
    local absolute_path=$(atae_cfg_get_file_section_key_value ${conf_file} ${section} "absolute_path")
    local paths=$(ls -d ${absolute_path} 2>/dev/null)
    if [[ -z ${paths} ]];then
        log_cmd ${output} "no such dir: ${paths}"
        return 0
    fi
    local file_names=$(atae_cfg_get_file_section_key_value ${conf_file} ${section} "file_names")
    for path in ${paths} ;do
        if [[ -z ${file_names} ]] ;then
            log_cmd ${output} "ls ${path}"
            file_names=$(ls ${path} 2>/dev/null)
        fi
        for file_name in ${file_names} ;do
            file_name="${path}/${file_name}"
            [[ ! -f ${file_name} ]] && continue
            [[ -n ${format} ]] && file_name="${file_name} | ${format}"
            log_cmd ${output} "cat ${file_name} 2>/dev/null"
        done
    done
}


function collector_file()
{
    local conf_file=$1
    local section=$2
    local output=$3
    local format=$(atae_cfg_get_file_section_key_value ${conf_file} ${section} "format")
    local get_cmd=$(atae_cfg_get_file_section_key_value ${conf_file} ${section} "get_files_cmd_${OS_NAME}")
    [[ -z ${get_cmd} ]] && get_cmd=$(atae_cfg_get_file_section_key_value ${conf_file} ${section} "get_files_cmd_common")
    local dst_files=$(atae_cfg_get_file_section_key_value ${conf_file} ${section} "dst_file_${OS_NAME}")
    [[ -z ${dst_files} ]] && dst_files=$(atae_cfg_get_file_section_key_value ${conf_file} ${section} "dst_file_common")
    [[ -n ${get_cmd} ]] && dst_files="$(bash -c "${get_cmd}" 2>/dev/null) ${dst_files}"
    for file in ${dst_files} ;do
        if [[ -n ${file} && ! -f ${file} ]] ;then
            log_cmd ${output} "no such file:${file}"
            continue
        fi
        if [[ -n ${file} && -f ${file} ]] ;then
            [[ -n ${format} ]] && file="${file} | ${format}"
            log_cmd ${output} "cat ${file}"
        fi
    done
}

function collector_command()
{
    local conf_file=$1
    local section=$2
    local output=$3
    local cmd=$(atae_cfg_get_file_section_key_value ${conf_file} ${section} "cmd_${OS_NAME}")
    [[ -z "${cmd}" ]] && cmd=$(atae_cfg_get_file_section_key_value ${conf_file} ${section} "cmd_common")
    [[ -n "${cmd}" ]] && local cycle_range=$(atae_cfg_get_file_section_key_value ${conf_file} ${section} "scope")
    if [[ -n "${cmd}" ]] ;then
        if [[ -n "${cycle_range}" ]] ;then
            for i in $(echo "${cycle_range}" | bash) ;do
                log_cmd "${output}" "${cmd} ${i}"
            done
        else
            log_cmd "${output}" "${cmd}"
        fi
    fi
    return 0
}


function collector_other()
{
    local conf_file=$1
    local section=$2
    local output=$3
    local script=$(atae_cfg_get_file_section_key_value ${conf_file} ${section} "script_${OS_NAME}")
    [[ -z ${script} || ! -f ${CUR_DIR}/scripts/${script} ]] && script=$(atae_cfg_get_file_section_key_value ${conf_file} ${section} "script_common")
    [[ -f ${CUR_DIR}/scripts/${script} ]] && bash ${CUR_DIR}/scripts/${script} ${output}
}


function main()
{
    config_init || return 1
    cd ${CUR_DIR} || return 1
    local conf_files=$(find collect_items -type f -name '*.conf' | sed 's/^collect_items\///g')
    cd - >/dev/null 2>&1 || return 1
    [[ -e ${LOG_PATH} ]] && rm -rf ${LOG_PATH}
    mkdir -p ${LOG_PATH}
    for conf_file in ${conf_files} ;do
        local collect_dir=${LOG_PATH}/$(dirname ${conf_file})
        [[ -d ${collect_dir} ]] || mkdir -p ${collect_dir}
        local type_name=$(awk -F'.' '{print $1}' <<< "$(basename ${conf_file})")
        printlog "${type_name}..."
        local output_file=${collect_dir}/${type_name}.txt
        local sections=$(atae_cfg_get_file_sections ${CUR_DIR}/collect_items/${conf_file})
        for section in ${sections} ;do
            local collector_type=$(awk -F'_' '{print $1}' <<< "${section}")
            collector_${collector_type} ${CUR_DIR}/collect_items/${conf_file} ${section} ${output_file}
        done
        echolog Done
    done
    if [[ ! -d ${UPLOAD_DIR} ]]; then
        mkdir -p ${UPLOAD_DIR}
    fi
    echolog "cp -rf ${LOG_PATH} ${UPLOAD_DIR}"
    cp -rf ${LOG_PATH}/* ${UPLOAD_DIR}/
    if [  $? -ne 0 ];then
        echolog "cp failed"
        return 1
    fi
    return 0
}

main "$@"
exit $?