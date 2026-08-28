# from own_funktions import ValueBuffer
from collections import Counter, defaultdict
import ast
import ctypes
import json
from pathlib import Path
try:
    from own_functions import tolist
except:
    from Vision_Robotic_Arm_Gesture_Recognition.own_functions import tolist


def rename_files(folder: str, old: str, new: str) -> int:
    """
    Ersetzt in allen Dateinamen eines Ordners den String `old` durch `new`.

    Gibt die Anzahl der umbenannten Dateien zurück.
    """

    count = 0

    for file in Path(folder).iterdir():
        if not file.is_file():
            continue

        if old in file.name:
            new_name = file.name.replace(old, new)
            file.rename(file.with_name(new_name))
            count += 1

    return count

from pathlib import Path


from pathlib import Path


def find_files(
    folder: str,
    ending: str | list[str] | None = None,
    starts_with: str | list[str] | None = None,
    contains: str | list[str] | None = None,
    names_only: bool = False,
) -> list[str]:
    """
    Sucht Dateien in einem Ordner.

    Die Parameter ending, starts_with und contains können jeweils
    entweder ein String oder eine Liste von Strings sein.
    """
    folder = Path(folder)

    endings = tolist(ending)
    prefixes = tolist(starts_with)
    substrings = tolist(contains)

    if endings:
        endings = [
            e if e.startswith(".") else "." + e
            for e in endings
        ]

    result = []

    for file in folder.iterdir():
        if not file.is_file():
            continue

        name = file.name
        if endings is not None and file.suffix not in endings:
            continue

        if prefixes is not None and not any(name.startswith(p) for p in prefixes):
            continue

        if substrings is not None and not any(s in name for s in substrings):
            continue

        result.append(name if names_only else str(file))

    return result


def save_dict_to_json(filename: str, data: dict) -> None:
    if not data:
        print("No data to save.")
        return
    with open(filename, "w", encoding="utf-8") as f:
        for key, value in data.items():
            f.write(json.dumps([key, value], ensure_ascii=False) + "\n")
        print(f"Saved {len(data)} status to {filename}.")

def load_dict_from_json(filename: str, data:dict={}) -> dict:
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                key, value = json.loads(line)
                data[key] = value

    return data

def save_list_to_file(filename, data:tuple=None):
    if not data:
        print("No data to save.")
        return
    with open(filename, 'w') as f:
        for item in data:
            f.write(f"{item}\n")
        print(f"Saved {len(data)} status to {filename}.")

def load_list_from_file(filename, data:list=[]) -> list:
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data.append(ast.literal_eval(line)) # ast txt, alternative to json file

    return data

def key_pressed(vk_code):
    return ctypes.windll.user32.GetAsyncKeyState(vk_code) & 0x8000 != 0

class CaptureStatus:
    def __init__(self, keys:list, status:list=None):
        if status is None:
            try:
                status = keys.copy()
            except:
                status = keys
        self.keys = keys
        self.status = status
        self.saved = []
    
    def add(self, key, if_no_key_match_add_none=True):
        if key in self.keys:
            index = self.keys.index(key)
            self.saved.append(self.status[index])
            return self.status[index]
        elif if_no_key_match_add_none:
            self.saved.append(None)
        else:
            return None
    
    def add_from_pressed_key(self, if_no_key_match_add_none=True, add_only_first=False):
        add = []
        
        for i, key in enumerate(self.keys):
            if key_pressed(key):
                add.append(self.status[i])
        
        if not add and if_no_key_match_add_none:
            add.append(None)
        
        if add_only_first:
            add = add[0]

        self.saved.append(add)

        return add if add else None

    def shift_all_by(self, i:int, fill = None):
        if type(self.saved[0]) is list and type(fill) is not list:
            fill = [fill]

        fill = [fill]*abs(i)
        lost = None
        if i >= 1:
            lost = self.saved[:i]
            self.saved = fill + self.saved[i:]
        elif i <= -1:
            lost = self.saved[i:]
            self.saved = self.saved[:i] + fill
        return lost, fill

    def save_to_file(self, filename, data:tuple=None):
        if not data:
            data = self.saved
        save_list_to_file(filename=filename,data=data)
    
    def load_from_file(self, filename, data:list=None):
        if data is None:
            data = self.saved
        load_list_from_file(filename=filename, data=data)
        # if self.saved == data:
        #     if self.status is None:
        #         self.status = list(set(data))
        #         if self.keys is None:
        #             self.keys = self.status.copy()
    
    def get(self, index):
        if index < len(self.saved):
            return self.saved[index]
        else:
            return None
        
    def pop(self, i:int=-1):
        if self.saved:
            return self.saved.pop(i)


class SaveFrameStatus(CaptureStatus):
    def __init__(self, keys, status = None):
        super().__init__(keys, status)
        self.pop_key = ord('x')
        self.status_for_each_frame = []
        self.status_for_each_frame_comp = []

    def add(self, start_frame, key, print_out=True):
        if key in self.keys:
            i = self.keys.index(key)
            add = [start_frame, self.status[i]]
            self.saved.append(add)
            if print_out:
                print('Frame', start_frame, '-', self.status[i])
        elif key == self.pop_key:
            wrong = self.pop()
            if wrong:
                if print_out:
                    print('pop: Frame', wrong[0], '-', wrong[1])
                return wrong[0]
            else:
                if print_out:
                    print('empty - nothing to pop')

    def get_status_for_each_frame(self,):
        if not self.status_for_each_frame:
            self.create_status_for_each_frame()
        return self.status_for_each_frame

    def create_status_for_each_frame(self, transform_status=True):
        if not self.saved:
            raise Exception('no self.saved data to transform')
        
        self.status_for_each_frame.clear() # just in case
        status = None # start startus
        f_nr = 0 # start frame nr

        # for each saved startus change in saved
        for start_frame, next_status in self.saved:
            # add the same status until the start frame of the next status is reached
            while f_nr < start_frame:   
                self.status_for_each_frame.append(status)
                f_nr += 1 

            status = next_status
            if transform_status:
                status = self.to_0_1(status)
        
        # add last status only ons for all remaining frames 
        self.status_for_each_frame.append(status)
    
    def to_0_1(self, status):
        if status == 'hand open': return 1
        if status == 'hand closed': return 0
        return status

    def check_frame_order(self):
        frame_nr_before = -1
        for save in self.saved:
            f_nr = save[0]
            if f_nr > frame_nr_before:
                frame_nr_before = f_nr
            else:
                raise Exception(f'Frame order Error: {f_nr} folows {frame_nr_before}')
    
    def add_comparison_status(self, status, if_no_match_add_none=True):
        if status in self.status:
            self.status_for_each_frame_comp.append(status)
        elif if_no_match_add_none:
            self.status_for_each_frame_comp.append(None)

    def load_comp_from_file(self, filename, start_frame=1):
        self.status_for_each_frame_comp.clear()
        data = self.status_for_each_frame_comp
        super().load_from_file(filename=filename, data=data)
        if start_frame > 1:
            self.set_comp_start_frame(start_frame=start_frame)

    def load_from_file(self, filename):
        r = super().load_from_file(filename)
        # self.change_str_to_int()
        self.check_frame_order()
        return r
    
    def save_comp_to_file(self, filename:str):
        if not self.status_for_each_frame_comp:
            print('no compare data to save')
        if not self.status_for_each_frame:
            try:
                self.create_status_for_each_frame()
            except:
                print('no saved data there, just save saved_comp data')
                data = self.status_for_each_frame_comp
                
        if self.status_for_each_frame:
            print('saving zip[saveed, saved_comp] data for each frame')
            data = zip(self.status_for_each_frame, self.status_for_each_frame_comp)

        return super().save_to_file(filename, data)

    def extend_comp(self, front=[], beck=[]):
        self.status_for_each_frame_comp = front + self.status_for_each_frame_comp + beck

    def set_comp_start_frame(self, start_frame=1):
        """
            use if compareson data capturing started later at frame: startframe 
            startframe = 1 means no change
        """
        front_extension = [None]*(start_frame-1)
        self.extend_comp(front=front_extension)
        return len(self.status_for_each_frame_comp)

    def copare_fram_by_frame(self):
        results = {
            'compared frames':0,
            'None':0,
            'open_right':0,
            'open_false':0,
            'closed_right':0,
            'closed_false':0,
            'open_not_detected':0,
            'closed_not_detected':0,
        }
        if not self.status_for_each_frame_comp:
            raise Exception('no data to compare with, no: status_for_each_frame_comp')
        if not self.status_for_each_frame:
            self.create_status_for_each_frame()

        l1 = len(self.status_for_each_frame)
        l2 = len(self.status_for_each_frame_comp)
        shorter = min(l1,l2)

        for i in range(shorter):
            s_should = self.status_for_each_frame[i]
            s_is = self.status_for_each_frame_comp[i]
            key = self.compare_status(s_should=s_should, s_is=s_is)
            results['compared frames'] += 1
            results[key] += 1
        
        return self.evaluate_comparison(results)
    
    def evaluate_comparison(self, results):

        total_right = results['open_right'] + results['closed_right']
        total_false = results['open_false'] + results['closed_false']
        not_detected = results['open_not_detected'] + results['closed_not_detected']
        importent_frames = total_right + total_false + not_detected
        right_rate = round(100*total_right / importent_frames, 1)
        false_rate = round(100*total_false / importent_frames, 1)
        not_detected_rate = round(100*not_detected / importent_frames, 1)

        results['importent_frames'] = importent_frames
        results['total_right'] = total_right
        results['right_rate'] = right_rate
        results['total_false'] = total_false
        results['false_rate'] = false_rate
        results['not_detected'] = not_detected
        results['not_detected_rate'] = not_detected_rate

        return results


    def compare_status(self, s_should, s_is):
        if s_should is None: # skip not importent frames
            return 'None'
        # open hand detected
        if s_is == 1: 
            if s_should == 1: # should be open
                return 'open_right'
            return 'open_false'
        # closed hand detected
        if s_is == 0:
            if s_should == 0: # should be closed
                return 'closed_right'
            return 'closed_false'
        # no hand detected
        if s_is == None:
            if s_should == 1: # should be open
                return 'open_not_detected'
            if s_should == 0: # should be closed
                return 'closed_not_detected'


def results_for_parameters(parameters:list, results:dict, destination_folder:str, save=False, avarage_min_max=False):
     # indexes for each name containing the methode combination name
    names = results['name']
    parameters_indexes = defaultdict(list)
    for parameter in parameters:
        for i, name in enumerate(names):
            if parameter in name:
                parameters_indexes[parameter].append(i)

    # results for each methode_data_file_names
    parameter_results_dict = defaultdict(list)
    for parameter in parameters_indexes:
        indexes = parameters_indexes[parameter]
        parameter_results = defaultdict(list)
        for i in indexes:
            for key in results:
                parameter_results[key].append(results[key][i])

        # average for each result key

        for key in parameter_results:
            if key == 'name':
                parameter_results[key].insert(0, f'{parameter}_average')
                continue
            values = parameter_results[key]
            if 'rate' in key:
                average = round(sum(values)/len(values), 1)
            else:
                average = round(sum(values)/len(values))
            parameter_results[key].insert(0, average)


        parameter_results_dict[parameter] = parameter_results
        if save:
            save_dict_to_json(destination_folder+f'/hand_detection_parameter_results_{parameter}.comp',parameter_results)
    
    if avarage_min_max:
        # min max parameter of the average results for each key
        average_results = defaultdict(list)
        for parameter in parameter_results_dict:
            resupts = parameter_results_dict[parameter]
            average_results['name'].append(parameter)
            for key in resupts:
                average_results[key].append(resupts[key][0])
        save_dict_to_json(destination_folder+f'/hand_detection_parameter_results_average.comp',average_results)
        return find_min_max(average_results, save=True, save_file_name=destination_folder+f'/hand_detection_parameter_results_average_min_max.comp')

    return parameter_results_dict

def get_name_from_path(path:str):
    return Path(path).stem

def process_one_video(right_file:str, comp_files:list[str],  results:defaultdict=None, save_folder:str='',save=False,start_frame=1):
    print('--------------analysiren-----------------')
    if results is None or save:
        results = defaultdict(list)
    fs = SaveFrameStatus(None)
    fs.load_from_file(right_file)
    
    for file_path in comp_files:
        name = get_name_from_path(file_path)
        results['name'].append(name)
        fs.load_comp_from_file(file_path,start_frame=start_frame)
        result = fs.copare_fram_by_frame()
        for key in result:
            results[key].append(result[key])
    if save:
        video = get_name_from_path(right_file)[:3]
        save_dict_to_json(save_folder+f'hand_detection_resunls_{video}.comp',results)
    
    return results

def find_min_max(data:dict, results:defaultdict=None, save=False, save_file_name:str='compare_file'):
    if results is None:
        results = defaultdict(list)

    keys = [
        'name',
        'importent_frames',
        'total_right',
        'right_rate',
        'total_false',
        'false_rate',
        'not_detected',
        'not_detected_rate',
    ]
    for key in ['right_rate','false_rate', 'not_detected_rate']:
        d = data[key]

        dmax = max(d)
        i = d.index(dmax)
        name = data['name'][i]
        results['max_'+key].append([name,dmax])

        dmin = min(d)
        i = d.index(dmin)
        name = data['name'][i]
        results['min_'+key].append([name,dmin])

    if save:
        save_dict_to_json(save_file_name,results)
    
    return results

def get_files_for_one_video(video:str, right_folder:str, comp_folder:str, name_only=False):
    right_file = find_files(right_folder,ending='txt', starts_with=video, names_only=name_only)
    comp_files = find_files(comp_folder,ending='txt',starts_with=video, names_only=name_only)
    if len(right_file) != 1:
        raise Exception(f'found {len(right_file)} right files for video {video}, should be 1')
    if len(comp_files) < 1:
        raise Exception(f'found {len(comp_files)} comp files for video {video}, should be >= 1')
    
    return right_file, comp_files
  
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

def process_all():
    right_folder = r"C:\Users\Ampelman\Desktop\Masterarbeit\open close status data for videos/"
    comp_folder = r"C:\Users\Ampelman\Desktop\Masterarbeit\open close status data for videos\average3_pos_buffer_test/"
    destination_folder = r'C:\Users\Ampelman\Desktop\Masterarbeit\open close status data for videos\average3_pos_buffer_test\results/'
    right_files = find_files(right_folder,ending='txt', names_only=True)
    comp_files = find_files(comp_folder,ending='txt', names_only=True)
    methodes = [
        'aperture_7050', 
        'aperture_7065', 
        'aperture_7060',
        'dif_0.6',
        'dif_1.0',
        'dif_1.4'
    ]
    methode_data_file_names = find_files(comp_folder,ending='txt', starts_with='v1_', names_only=True)
    for i, combi in enumerate(methode_data_file_names):
        start_i = combi.find('-') + 1
        end_i = combi.find('.txt')
        methode_data_file_names[i] = combi[start_i:end_i]
    print('methode combinations found:', len(methode_data_file_names))

    videos =[
        'v01_',
        'v02_',
        'v03_',
        'v04_',
        'v05_',
    ]

    # results vor all videos and all methodes, one file fore each video
    results=defaultdict(list)
    for v in videos:
        right_files, comp_files = get_files_for_one_video(v, right_folder=right_folder, comp_folder=comp_folder)
        print(f'use video {v} to compare to {len(comp_files)} compare files')
        process_one_video(right_file=right_files[0], comp_files=comp_files, save=False, results=results, save_folder=destination_folder,start_frame=1)

    # results for each combination of methodes and vedio
    results_for_parameters(
        parameters=methode_data_file_names, 
        results=results, destination_folder=destination_folder+'/methode_results_for_each_video', 
        save=False,
        avarage_min_max=False
    )
    # results for each detection methodes
    results_for_parameters(
        parameters=methodes, 
        results=results, destination_folder=destination_folder+'/methode_results', 
        save=True, avarage_min_max=False
    )
       

    # # get max min values for each video and save to one file
    # results_min_max = defaultdict(list)
    # for v in videos:
    #     right_files, comp_files = get_files_for_one_video(v, right_folder=right_folder, comp_folder=comp_folder)
    #     results0 = process_one_video(right_file=right_files[0], comp_files=comp_files, save=False)
    #     # for name in results0['name']:
    #     #     print(name)
    #     find_min_max(results0,results=results_min_max)

    # save_dict_to_json(destination_folder+f'/hand_detection_results_min_max_v1-5.comp',results_min_max)



if __name__ == '__main__':
    process_all()

