#! /bin/bash

function log_cmd()
{
    local log_file=$1
    shift
    local cmd_name=$(echo $@ | awk '{print $1}')
    local cmd_path=$(\which $cmd_name 2>/dev/null | awk '{print $1}')
    local exit_code=0
    echo "#=====[ COMMAND ]===================================#" >> ${log_file}
    if [[ -x "${cmd_path}" ]] ;then
        local bincmd_line=$(echo $@ | sed 's!${cmd_name}!${cmd_path}!')
        echo "# $bincmd_line" >> ${log_file} 2>&1
        echo "$bincmd_line" | bash >>${log_file} 2>&1
    else
        echo "# $cmd_name" >> ${log_file}
        echo "ERROR: Command is not exists or inexecutable!" >> ${log_file}
    fi

    echo "" >> ${log_file}
    return 0
}
export -f log_cmd

function echolog()
{
    echo "$@" | tee -a ${LOG_FILE}
}
export -f echolog

function printlog()
{
        printf "  %-45s" "$@" | tee -a ${LOG_FILE}
}
export -f printlog

function conf_files() {
    local log_file=$1
    shift
    local files=$@
    local file_name
    for file_name in $files
    do
        echo "#=====[ CONFIGURATION FILE ]========================#" >> ${log_file}
        if [ -f $file_name ]; then
            echo "# $file_name" >> ${log_file}
            sed -e '/^[[:space:]]*#/d' -e '/^[[:space:]]*;/d' -e '/^[[:space:]]*\/\//d' -e 's///g' -e '/^$/d' ${file_name} >> ${log_file}
            echo "" >> ${log_file}
        else
            echo "# $file_name: File not exists" >> ${log_file}
        fi

        echo >> ${log_file}
    done
}
export -f conf_files