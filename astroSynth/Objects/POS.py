import os
import time
import names
import shutil
import numpy as np
import pandas as pd
from tqdm import tqdm
from sys import getsizeof
from astroSynth import PVS
from astroSynth import SDM
from astropy import units as u
from tempfile import TemporaryFile


class POS():
	def __init__(self, prefix='SynthStar', mag_range=[10, 20], noise_range=[0.1, 1.1],
		         number=1000, numpoints=300, verbose=0, name=None):
		if name is None:
			name = prefix
		self.name = name
		self.prefix = prefix
		self.mag_range = mag_range
		self.size = number
		self.depth = numpoints
		self.verbose = 0
		self.noise_range = noise_range
		self.targets = dict()
		self.int_name_ref = dict()
		self.name_int_ref = dict()
		self.classes = dict()
		self.target_ref = dict()
		self.dumps = dict()
		self.state = -1

	@staticmethod
	def __load_spec_class__(path):
		file_data = open(path, 'rb')
		file_data = file_data.decode('utf-8')
		file_data = file_data.readlines()
		file_data = [x.rstrip().split(':') for x in file_data]
		amp_range = None
		phase_range = None
		freq_range = None
		L_range = None
		for i, e in enumerate(file_data):
			if i[0] == 'amp_range':
				amp_range = i[1]
			elif i[0] == 'freq_range':
				freq_range = i[1]
			elif i[0] == 'phase_range':
				phase_range = i[1]
			elif i[0] == 'L_range':
				L_range = i[1]
			else:
				print('Warning! Unkown line encountered -> {}:{}'.format(i[0], i[1]))
		return amp_range, phase_range, freq_range, L_range

	@staticmethod
	def __seed_generation__(seed=1):
		np.random.seed(seed)

	def __build_survey__(self, amp_range=[0, 0.2],freq_range = [1, 100],
	  		  			 phase_range=[0, np.pi], L_range=[1, 3],
    		  			 amp_varience=0.01, freq_varience=0.01, 
    		  			 phase_varience=0.01,  obs_range=[10, 100]):
		for i in tqdm(range(self.size)):
			pulsation_modes = np.random.randint(L_range[0],
				                                L_range[1] + 1)

			pulsation_amp = np.random.uniform(amp_range[0],
				                              amp_range[1])#,
				                              #pulsation_modes)
			pap = amp_varience * pulsation_amp

			pulsation_frequency = np.random.uniform(freq_range[0],
				                                    freq_range[1])#,
				                                    #pulsation_modes)
			pfp = freq_varience * pulsation_frequency

			pulsation_phase = np.random.uniform(phase_range[0],
		    	                                phase_range[1])#,
		    	                                #pulsation_modes)
			ppp = phase_varience * pulsation_phase

			observations = np.random.randint(obs_range[0],
											 obs_range[1])

			target_name = names.get_full_name().replace(' ', '-')
			target_id = "{}_{}".format(self.prefix, target_name)
			self.targets[target_id] = PVS(Number=observations, numpoints=self.depth, 
				                          verbose=self.verbose, noise_range=self.noise_range, 
				                          mag_range=self.mag_range, name=target_id, 
				                          lpbar=False, ftemp=True, single_object=True)

			self.targets[target_id].build(amp_range=[pulsation_amp - pap, pulsation_amp + pap],
										  freq_range=[pulsation_frequency - pfp, pulsation_frequency + pfp],
										  phase_range=[pulsation_phase - ppp, pulsation_phase + ppp],
										  L_range=[pulsation_modes, pulsation_modes])
			self.int_name_ref[i] = target_id
			self.name_int_ref[target_id] = i

	def __get_break_params__(self, break_number_range=[0, 10]):
		"""
		Currently Experimental
		"""
		return ([], []), ([], [])


	def build(self, load_from_file = False, path=None, amp_range=[0, 0.2], 
		      freq_range = [1, 100], phase_range=[0, np.pi], L_range=[1, 3], 
		      amp_varience=0.01, freq_varience=0.01, phase_varience=0.01, 
		      seed=1, visits=[10, 100]):
		if load_from_file is True:
			try:
				assert path is not None
			except AssertionError as e:
				e.arge += ('Error! No Path to file given', 'Did you specify path?')

				raise

		self.__seed_generation__(seed=seed)

		if load_from_file is True:
			ar, pr, fr, lr = self.__load_spec_class__(path)
			if ar is not None:
				amp_range = ar
			if pr is not None:
				phase_range = pr
			if fr is not None:
				freq_range = fr
			if lr is not None:
				L_range = lr

		self.__build_survey__(amp_range=amp_range, L_range=L_range, freq_range=freq_range,
							  phase_range=phase_range, amp_varience=amp_varience,
							  phase_varience=phase_varience, freq_varience=freq_varience,
							  obs_range=visits)

	def generate(self, pfrac=0.5, target_in_mem=100, vtime_units=u.hour,
				 btime_units=u.day, exposure_time=30, visit_range=[1, 10],
				 visit_size_range=[0.5, 2], break_size_range=[10, 100],
				 etime_units=u.second):
		dumpnum = 0
		lastdump = 0
		for j, i in tqdm(enumerate(self.targets), desc='Geneating Survey Data', total=self.size):
			rand_pick = np.random.uniform(0, 10)
			if rand_pick < pfrac * 10:
				self.classes[i] = 1
			else:
				self.classes[i] = 0
			self.targets[i].generate(pfrac=self.classes[i], vtime_units=vtime_units,
				                     btime_units=btime_units, exposure_time=exposure_time,
				                     visit_range=visit_range, visit_size_range=visit_size_range,
				                     break_size_range=break_size_range, etime_units=etime_units)
			if j-lastdump >= target_in_mem:
				path_a = "{}/.{}_temp".format(os.getcwd(), self.prefix)
				if os.path.exists(path_a):
					shutil.rmtree(path_a)
				os.mkdir(path_a)
				path = "{}/.{}_temp/{}_dump".format(os.getcwd(), self.prefix, dumpnum)
				os.mkdir(path)
				for k, x in enumerate(self.targets):
					if k < j-lastdump: 
						star_path = "{}/{}".format(path, x)
						os.mkdir(star_path)
						self.targets[x].save(path=star_path)
						self.targets[x] = None
				self.target_ref[dumpnum] = [lastdump, target_in_mem + lastdump - 1]
				self.dumps[dumpnum] = path
				dumpnum += 1
				lastdump = j
		self.target_ref[-1] = [lastdump, self.size - 1]

	def __get_target_id__(self, n):
		if isinstance(n, int):
			target_id = self.int_name_ref[n]
		if isinstance(n, str):
			target_id = n
		return target_id

	def __get_lc__(self, n=0, full=True, sn=0, start=0, stop=None):
		if isinstance(n, int):
			target_id = self.int_name_ref[n]
		if isinstance(n, str):
			target_id = n
		if stop == None:
			stop = len(self.targets[target_id])
		if full is True:
			times = list()
			fluxs = list()
			for Time, Flux, classes, _ in self.targets[target_id].xget_lc(start=start,
				                                                          stop=stop):
				times.extend(Time)
				fluxs.extend(Flux)
				c = classes
		else:
			times = self.targets[target_id][sn][0]
			fluxs = self.targets[target_id][sn][1]
			c = self.targets[target_id][sn][2]
		return times, fluxs, c, n, full, sn

	def xget_lc(self, start=0, stop=None):
		if stop is None:
			stop = self.size
		if stop > self.size:
			stop = self.size
		for i in range(start, stop):
			yield self.__get_lc__(n=i)

	def get_lc_sub(self, n=0, sub_element=0):
		return self.__get_lc__(n=n, full=False, sn=sub_element)


	def __get_spect__(self, n=0, s=500, UD_stretch=250, LD_stretch=1):
		if isinstance(n, int):
			target_id = self.int_name_ref[n]
		if isinstance(n, str):
			target_id = n
		Amps = list()
		for Freq, Amp, Class, Index in self.targets[target_id].xget_ft():
			Amps.append(Amp)
		return np.repeat(np.repeat(Amps, LD_stretch, axis=1),UD_stretch, axis=0), Freq

	def xget_spect(self, start=0, stop=None, s=500, UD_stretch=250,
		           LD_stretch=1):
		if stop is None:
			stop = self.size
		if stop > self.size:
			stop = self.size
		for i in range(start, stop):
			yield self.__get_spect__(n=i, s=s, UD_stretch=UD_stretch,
									 LD_stretch=LD_stretch)

	def get_ft_sub(self, n=0, sub_element=0, s=500):
		target_id = self.__get_target_id__(n)
		return self.targets[target_id].get_ft(n=sub_element, s=s)

	def __load_dump__(self, n=0, state_change=True):
		if state_change is True:
			self.targets = dict()
			self.state = n
		else:
			ttargets = dict()
		try:
			assert n >= -1 and n < len(self.dumps)
		except AssertionError as e:
			e.args += ('ERROR! Dump index {} out of range for dump of size {}'.format(n, len(self.dumps)))
			raise
		dump_path = self.dumps[n]
		load_targets = os.listdir(dump_path)
		for target in load_targets:
			load_path = "{}/{}".format(dump_path, target)
			if state_change is True:
				self.targets[target] = PVS()
				self.targets[target].load(load_path)
			else:
				ttargets[target] = PVS()
				ttargets[target].load(load_path)
		if state_change is False:
			return ttargets
		else:
			return 0

	def __get_target_lc__(self, target=0, n=0, state_change=False):
		if isinstance(target, int):
			try:
				assert target < self.size
			except AssertionError as e:
				e.args += ('ERROR!, Target Index Out Of Range')
				raise

			target_id = self.int_name_ref[n]
			target_num = target
		elif isinstance(target, str):
			try:
				assert target in self.targets
			except AssertionError as e:
				e.args('Error! Target Index not found in targets reference')
				raise
			try:
				assert n < len(self.targets)
			except AssertionError as e:
				e.args += ('ERROR! Target Light Curve index out of range')
				raise

			target_id = target
			target_num = self.name_int_ref[target_id]

		dump_num = -1
		for k in self.target_ref:
			if int(self.target_ref[k][0]) <= target_num <= int(self.target_ref[k][1]):
				dump_num = int(k)
				break

		if dump_num != self.state:
			pull_from = self.__load_dump__(n=dump_num, state_change=state_change)
			print('Targets are: {}'.format(self.targets))
			try:
				assert n < len(self.targets[self.int_name_ref[target]])
			except AssertionError as e:
				e.args += ('ERROR! Target Light Curve index out of range')
				raise
			if state_change is False:
				Time, Flux, Class, n = pull_from[target_id][n]
			else:
				Time, Flux, Class, n = self.targets[target_id][n]
		else:
			print('Targets are: {}'.format(self.targets))
			Time, Flux, Class, n = self.targets[target_id][n]

		return Time, Flux, Class, n, target_id

	def save(self, path=None):
		if path is None:
			path = "{}/{}".format(os.getcwd(), self.name)
		if os.path.exists(path):
			shutil.rmtree(path)
		os.mkdir(path)
		for dump in self.dumps:
			group_path = "{}/Group_{}".format(path, dump)
			if os.path.exists(group_path):
				shutil.rmtree(group_path)
			os.mkdir(group_path)
			data = self.__load_dump__(n=dump, state_change=False)
			for target in data:
				target_save_path = "{}/{}".format(group_path, target)
				if os.path.exists(target_save_path):
					shutil.rmtree(target_save_path)
				os.mkdir(target_save_path)
				data[target].save(path=target_save_path)
		mem_path = "{}/Group_-1".format(path)
		if os.path.exists(mem_path):
			shutil.rmtree(mem_path)
		os.mkdir(mem_path)	
		for target in self.targets:
			if self.targets[target] is not None:
				target_save_path = "{}/{}".format(mem_path, target)
				if os.path.exists(target_save_path):
					shutil.rmtree(target_save_path)
				os.mkdir(target_save_path)
				self.targets[target].save(path=target_save_path)
		self.__save_survey__(path)
		return path

	def __save_survey__(self, path):
		with open('{}/Object_Class.POS'.format(path), 'w') as f:
			out = list()
			for target in self.classes:
				out.append("{}:{}".format(target, self.classes[target]))
			out = '\n'.join(out)
			f.write(out)
		with open('{}/Item_Ref.POS'.format(path), 'w') as f:
			out = list()
			for target_id in self.int_name_ref:
				out.append("{}:{}".format(target_id, self.int_name_ref[target_id]))
			out = '\n'.join(out)
			f.write(out)
		with open("{}/Item_Loc.POS".format(path), 'w') as f:
			out = list()
			for dump in self.target_ref:
				out.append("{}:{}:{}".format(dump, self.target_ref[dump][0],
					                         self.target_ref[dump][1]))
			out = '\n'.join(out)
			f.write(out)
		with open("{}/Object_Meta.POS".format(path), 'w') as f:
			out = list()
			out.append('Size:{}'.format(self.size))
			out.append('Name:{}'.format(self.name))
			out.append('Prefix:{}'.format(self.prefix))
			out.append('Depth:{}'.format(self.depth))
			out.append('Verbose:{}'.format(self.verbose))
			out.append('Noise:{}:{}'.format(self.noise_range[0],
										    self.noise_range[1]))
			out.append('MagRange:{}:{}'.format(self.mag_range[0],
											   self.mag_range[1]))
			out = '\n'.join(out)
			f.write(out)

	def load(self, directory='.', start=0):
		files = os.listdir(directory)
		try:
			assert 'Item_Loc.POS' in files
		except AssertionError as e:
			e.args += ('Error! Corrupted POS object', 'Cannot find "Item_Loc.POS"')
			raise
		try:
			assert 'Item_Ref.POS' in files
		except AssertionError as e:
			e.args += ('Error! Corrupted POS object', 'Cannot find "Item_Red.POS"')
			raise
		try:
			assert 'Object_Class.POS' in files
		except AssertionError as e:
			e.args += ('Error! Corrupted POS object', 'Cannot find "Object_Class.POS"')
			raise
		try:
			assert 'Object_Meta.POS' in files
		except AssertionError as e:
			e.args += ('Error! Corrupted POS object', 'Cannot find "Object_Meta.POS"')
			raise
		if directory[-1] == '/':
			directory = directory[:-1]
		dumps = [x.split('_')[1] for x in files if not '.POS' in x and 'Group' in x]
		dump_dirs = ["{}/Group_{}".format(directory, x) for x in dumps]
		self.dumps = dump_dirs
		with open('{}/Item_Loc.POS'.format(directory), 'r') as f:
			for line in f.readlines():
				data = line.split(':')
				self.target_ref[int(data[0])] = [int(data[1]), int(data[2])]
		with open('{}/Item_Ref.POS'.format(directory), 'r') as f:
			for line in f.readlines():
				data = line.split(':')
				self.int_name_ref[int(data[0])] = data[1].rstrip()
				self.name_int_ref[data[1].rstrip()] = int(data[0])
		with open('{}/Object_Class.POS'.format(directory), 'r') as f:
			for line in f.readlines():
				data = line.split(':')
				self.classes[data[0].rstrip()] = int(data[1])
		with open('{}/Object_Meta.POS'.format(directory), 'r') as f:
			for line in f.readlines():
				data = line.split(':')
				if data[0] == 'Size':
					self.size = int(data[1])
				elif data[0] == 'Name':
					self.name = data[1]
				elif data[0] == 'Prefix':
					self.prefix = data[1]
				elif data[0] == 'Depth':
					self.depth = int(data[1])
				elif data[0] == 'Verbose':
					self.verbose = int(data[1])
				elif data[0] == 'Noise':
					self.noise_range = [float(data[1]), float(data[2])]
				elif data[0] == 'MagRange':
					self.mag_range = [float(data[1]), float(data[2])]
		for dump in dumps:
			self.__load_dump__(n=int(dump))
		self.state = start

	def __del__(self):
		path = "{}/.{}_temp".format(os.getcwd(), self.prefix)
		if os.path.exists(path):
			shutil.rmtree(path)