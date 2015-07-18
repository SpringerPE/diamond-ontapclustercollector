#!/usr/bin/env bash
#
# Diamond-ontap configuration script
# (c) 2013 Jose Riguera <jriguera@gmail.com>
# Licensed under GPLv3

TEMPLATE=''
DEF_TEMPLATE='vfiler-8.x.template'
CONF_FILE=''
DEF_CONF_FILE='OntapClusterCollector.conf'

# Other variables
PROGRAM=${PROGRAM:-$(basename $0)}
PROGRAM_DIR=$(cd $(dirname "$0"); pwd)
PROGRAM_DESC="Diamond-ontap configuration script"

##############################

# Print a message
echo_log() {
   logger -p local0.notice -t ${PROGRAM} "$@"
   echo "--$PROGRAM $(date '+%Y-%m-%d %T'): $@"
}

# error
error_log() {
    logger -p local0.err -t ${PROGRAM} "$@"
    echo "--$PROGRAM $(date '+%Y-%m-%d %T') ERROR: $@" 
}

# Print a message and exit with error
die() {
    error_log "$@"
    exit 1
}

# help
usage() {
    cat <<EOF
Usage:

    $PROGRAM  [-h | --help ] [-t | --template <file>] [-c | --conf <file>]
              <add|remove|list|init> [<netapp_name> [<ip> <user> <password>]]

$PROGRAM_DESC

Arguments:

   -h, --help         		Show this message
   -t, --template <file> 	Template file
   -c, --conf <file>		Configuration file

Actions for the service:

    add		Add a new system with the rest of parameters to the conf file
    remove	Remove the <netapp_name> system from the configuration file
    list	List the systems in the configuration file
    init	Initialize the configuration file

To add a new system, you have to pass the <ip>, <user> and <password>
After add or remove a system, you will need to restart diamond.

EOF
}

backup_action() {
    local infile=$1
    local outfile=$2

    local rvalue

    [ -e $infile ] || return 0
    echo_log "Doing a backup of '$infile' ..."
    cp -a $infile $outfile
    rvalue=$?
    if [ $rvalue == 0 ]; then
        echo_log "Backup done to '$outfile'"
    else
        error_log "Error writing to '$outfile'"
    fi
    return $rvalue
}

delete_action() {
    local infile=$1
    local nick=$2

    local procnextline=1
    local entry
    local nickname
    local found=0
    local rvalue
    local counter=0
    local outfile="${infile}_$(date '+%Y%m%d%H%M%S')"

    backup_action $infile $outfile
    [ $? == 0 ] || return $rvalue
    echo_log "Removing '$nick' ... "
    rm -f $infile
    while IFS= read entry; do
        if echo $entry | grep -q "^#-END=.*"; then
            if [ $procnextline == 0 ]; then
                procnextline=1
                found=1
            else
                echo "$entry" >> $infile
            fi
        elif echo $entry | grep -q  "#-START=.*"; then
            nickname=$(echo $entry | sed -n 's/#-START=\(.*\)/\1/p')
            if [ "$nick" == "$nickname" ]; then
                procnextline=0
            else
            	echo "$entry" >> $infile
            fi
        elif [ $procnextline == 1 ]; then
            echo "$entry" >> $infile
        fi
        ((counter++))
    done < $outfile
    if [ $found == 1 ]; then
        echo_log "'$nick' was removed from $infile"
        rvalue=0
    else
        error_log "'$nick' was not found on $infile"
        rvalue=1
    fi
    return $rvalue
}

add_action() {
    local infile=$1
    local template=$2
    local nick=$3
    local ip=$4
    local user=$5
    local pass=$6

    local rvalue
    local outfile="${infile}_$(date '+%Y%m%d%H%M%S')"

    backup_action $infile $outfile
    [ $? == 0 ] || return $rvalue

    if ! grep -q "\[devices\]" $infile; then
	error_log "No valid configuration file. I have not found the section '[devices]' ... Initialize it first"
	return 1
    fi
    if grep -q "\[\[$nick\]\]" $infile; then
	error_log "Nick '$nick' is already defined!"
	return 1
    fi
    echo_log "Adding <$nick:$user:...pass...@$ip> ..."
    sed -e "s|@FILER@|$nick|g;s|@IP@|$ip|g;s|@USER@|$user|g;s|@PASSWORD@|$pass|g;" $template >> $infile
    rvalue=$?
    echo_log "'$nick' added to '$infile'."
    return $rvalue
}

init_action() {
    local infile=$1

    local outfile="${infile}_$(date '+%Y%m%d%H%M%S')"

    backup_action $infile $outfile
    [ $? == 0 ] || return $rvalue

    cat <<EOF > $infile
# Configuration file for Diamond-OntapClusterCollector

enabled = True
path_prefix = netapp
reconnect = 60
hostname_method = none
# Sequential or Threaded
method = Threaded
splay = 15
interval = 45

[devices]
# List of all configured devices

EOF
    echo_log "Default configuration file written."
    return 0
}

list_action() {
    local infile=$1

    local entry
    local nickname
    local nick
    local found_nick=0
    local errors=0
    local procnextline=0
    local counter=0


    if [ ! -r $infile ]; then
	error_log "No configuraton file '$inline' found!"
	return 1
    fi
    echo_log "Listing and checking configuration file $inline ... "
    while read entry; do
        if echo $entry | grep -q "^#-END=.*"; then
            nick=$(echo $entry | sed -n 's/#-END=\(.*\)/\1/p')
            if [ $procnextline == 1 ]; then
                procnextline=0
                if [ z"$nick" == z"$nickname" ] && [ $found_nick = 1 ]; then
                    echo "* '$nickname': ok"
                    ((counter++))
                else
                    echo "* '$nick': error, it did not have a [device] entry!"
                    ((errors++))
                fi
            else
                echo "* '$nick': error, it did not have START tag!"
                ((errors++))
            fi
            found_nick=0
        elif [ $procnextline == 1 ]; then
	    echo $entry | grep -q "\[\[$nickname\]\]" && found_nick=1
        elif echo $entry | grep -q  "#-START=.*"; then
            nickname=$(echo $entry | sed -n 's/#-START=\(.*\)/\1/p')
            procnextline=1
        fi
    done < $infile
    echo_log "$errors errors found."
    return $errors
}

# Main Program
# Parse the input
# See more in http://mywiki.wooledge.org/BashFAQ/035
OPTIND=1 # Reset is necessary if getopts was used previously in the script.
         # It is a good idea to make this local in a function.
while getopts "hdc:t:-:" optchar; do
    case "${optchar}" in
        -)
            # long options
            case "${OPTARG}" in
                help)
                    usage
                    exit 0
                ;;
                template)
                  eval TEMPLATE="\$${OPTIND}"
                  OPTIND=$(($OPTIND + 1))
                ;;
                conf)
                  eval CONF_FILE="\$${OPTIND}"
                  OPTIND=$(($OPTIND + 1))
                ;;
                *)
                    die "Unknown arg: ${OPTARG}"
                ;;
            esac
        ;;
        h)
            usage
            exit 0
        ;;
        t)
            TEMPLATE=$OPTARG
        ;;
        c)
            CONF_FILE=$OPTARG
        ;;
    esac
done
shift $((OPTIND-1)) # Shift off the options and optional --

if [ -z "$CONF_FILE" ]; then
    for path in /etc/diamond/diamond.conf /usr/local/etc/diamond/diamond.conf conf/diamond.conf diamond.conf; do
	if [ -e "$path" ]; then
	    CONF_FILE=$(sed -n 's/^[[:space:]]*collectors_config_path[[:space:]]*=[[:space:]]*\([[:print:]]*\).*/\1/p' $path)
            CONF_FILE=$(echo $CONF_FILE)/$DEF_CONF_FILE
	    break
        fi
    done
fi
[ -z "$CONF_FILE" ] && CONF_FILE=$DEF_CONF_FILE
[ -e "$CONF_FILE" ] || die "Configuration file '$CONF_FILE' not found"
[ -z "$TEMPLATE" ] && TEMPLATE="$(dirname ${CONF_FILE})/${DEF_TEMPLATE}"
echo_log "Using configuration file '$CONF_FILE'."
echo_log "Using template '$TEMPLATE'."

case "$1" in
    add)
        [ $# -ne 5 ] && die "Wrong number of arguments"
        add_action $CONF_FILE $TEMPLATE $2 $3 $4 $5
        exit $?
    ;;
    remove)
        [ $# -ne 2 ] && die "Wrong number of arguments"
	delete_action $CONF_FILE $2
        exit $?
    ;;
    list)
        list_action $CONF_FILE
        exit $?
    ;;
    init)
	init_action $CONF_FILE
	exit $?
    ;;
    *)
	die "Unknow action! See help!"
    ;;
esac
# EOF
