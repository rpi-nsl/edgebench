#!/bin/bash

# include the parse yaml script
# https://github.com/jasperes/bash-yaml

# Create the resource directories in the Raspberry Pi
create_directories(){
	# load the yaml library and get the variables in environment
	# __ double underscore for lists
	. yaml.sh
	create_variables ./config.yaml
	
	# Devices[@] gives the total number of devices
	number_of_devices=${#Devices[@]}
	# #GGDeviceDirectories__name[@] gives the number of elements in the array
	list_length=${#GGDeviceDirectories[@]}
	for (( j = 0 ; i < $number_of_devices ; j++ )); do
		ip=${Devices__ip[$j]}
		pass=${Devices__password[$j]}
		for (( i = 0 ; i < $list_length ; i++ )); do
			echo "Creating the ${GGDeviceDirectories[$i]} directory for Device ${Devices[$j]}"
			x=`sshpass -p $pass ssh pi@$ip "mkdir -p ${GGDeviceDirectories__actualpath[$i]} && sudo chmod 777 ${GGDeviceDirectories__actualpath[$i]} && mkdir ${GGDeviceDirectories__mountpath[$i]} && sudo chmod 777 ${GGDeviceDirectories__mountpath[$i]}"`
		done
	done
	echo "Done"
}


# Deletes the directories from the remote Edge Devices
delete_directories(){
	# load the yaml library and get the variables in environment
	# __ double underscore for lists
	. yaml.sh
	create_variables ./config.yaml
	
	# Devices[@] gives the total number of devices
	number_of_devices=${#Devices[@]}
	# #GGDeviceDirectories__name[@] gives the number of elements in the array
	list_length=${#GGDeviceDirectories[@]}
	for (( j = 0 ; i < $number_of_devices ; j++ )); do
		ip=${Devices__ip[$j]}
		pass=${Devices__password[$j]}
		for (( i = 0 ; i < $list_length ; i++ )); do
			echo "Deleting the ${GGDeviceDirectories[$i]} directory for Device ${Devices[$j]}"
			x=`sshpass -p $pass ssh pi@$ip "rm -rf ${GGDeviceDirectories__actualpath[$i]} && rm -rf ${GGDeviceDirectories__mountpath[$i]}"`
		done
	done
	echo "Done"

}

# from https://stackoverflow.com/a/16159057/8853476
# Check if the function exists (bash specific)
if declare -f "$1" > /dev/null
then
  # call arguments verbatim
  "$@"
else
  # Show a helpful error
  echo "'$1' is not a valid function name" >&2
  exit 1
fi


# set up directory structures
#create_directories
#delete_directories


