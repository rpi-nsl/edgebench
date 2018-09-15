import subprocess
import os

# Convert audio files to specific wav format for pocketshpinx

DIRNAME = "<input directory of audio files>"
OUTPUTDIR = "<output directory of audio files>"


def get_file_paths(dirname):
	file_paths = []  
	for root, directories, files in os.walk(dirname):
		for filename in files:
			filepath = os.path.join(root, filename)
			file_paths.append(filepath)  
	return file_paths


if __name__ == "__main__":
	all_files = get_file_paths(DIRNAME)
	response = subprocess.run(['mkdir', OUTPUTDIR], 
	                          shell = False, stderr=subprocess.PIPE)
	for file in all_files:
		new_filename = file.split(os.sep)[-1].split('.')[0]+ ".wav"
		response = subprocess.run(['ffmpeg', '-i', file, '-ar', '16000', '-ac', '1', os.path.join(OUTPUTDIR, new_filename)], 
	                          shell = False, stderr=subprocess.PIPE)
