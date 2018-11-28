import subprocess
import os
import argparse

"""
Convert audio files to specific wav format for pocketshpinx
According to : https://cmusphinx.github.io/wiki/faq/
"""
parser = argparse.ArgumentParser()
parser.add_argument('-s', "--source", help="Source Directory", required=True)
parser.add_argument('-d', "--destination", help="Destination Directory", required=True)
args = parser.parse_args()

Sourcdir = args.source
Destinationdir = args.destination


def get_file_paths(dirname):
	file_paths = []  
	for root, directories, files in os.walk(dirname):
		for filename in files:
			filepath = os.path.join(root, filename)
			file_paths.append(filepath)  
	return file_paths


if __name__ == "__main__":
	all_files = get_file_paths(Sourcdir)
	response = subprocess.run(['mkdir', Destinationdir], 
	                          shell = False, stderr=subprocess.PIPE)
	print("Converting all audio files to 16khz 16bit little-endian mono wav files")
	for file in all_files:
		new_filename = file.split(os.sep)[-1].split('.')[0]+ ".wav"
		response = subprocess.run(['ffmpeg', '-i', file, '-ar', '16000', '-ac', '1', os.path.join(Destinationdir, new_filename)], 
	                          shell = False, stderr=subprocess.PIPE)
