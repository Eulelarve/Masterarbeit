# from own_funktions import ValueBuffer
from collections import Counter
import ast
import ctypes
import json
from pathlib import Path

def get_files_with_extension(folder: str, extension: str) -> list[str]:
    """
    Gibt alle Dateien mit der angegebenen Endung in einem Ordner zurück.

    Beispiel:
        get_files_with_extension("data", ".txt")
        get_files_with_extension("images", "png")
    """
    extension = extension if extension.startswith(".") else "." + extension
    folder = Path(folder)

    return [str(file) for file in folder.iterdir()
            if file.is_file() and file.suffix == extension]


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

    def load_comp_from_file(self, filename, startframe=1):
        self.status_for_each_frame_comp.clear()
        data = self.status_for_each_frame_comp
        super().load_from_file(filename=filename, data=data)
        if startframe > 1:
            self.set_comp_start_frame(startframe=startframe)

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

    def set_comp_start_frame(self, startframe=1):
        """
            use if compareson data capturing started later at frame: startframe 
            startframe = 1 means no change
        """
        front_extension = [None]*(startframe-1)
        self.extend_comp(front=front_extension)
        return len(self.status_for_each_frame_comp)

    def copare_fram_by_frame(self):
        if not self.status_for_each_frame_comp:
            raise Exception('no data to compare with, no: status_for_each_frame_comp')
        if not self.status_for_each_frame:
            self.create_status_for_each_frame()

        l1 = len(self.status_for_each_frame)
        l2 = len(self.status_for_each_frame_comp)
        shorter = min(l1,l2)
        results = Counter()

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
        not_detected_rate = round(100*total_false / importent_frames, 1)

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

def process():
    print('--------------analysiren-----------------')
    right_folder = r"C:\Users\Ampelman\Desktop\Masterarbeit\open close status data for videos/"
    comp_folder = r"C:\Users\Ampelman\Desktop\Masterarbeit\open close status data for videos\methoden test/"
    right_files = get_files_with_extension(right_folder,'txt')
    comp_files = get_files_with_extension(comp_folder,'txt')
    fs = SaveFrameStatus(None)
    fs.load_from_file(right_files[0])
    fs.load_comp_from_file(comp_files[0],startframe=250)
    result = fs.copare_fram_by_frame()
    save_dict_to_json('test.json',result)
    print('---------------vergleichen----------------')
    pass





if __name__ == '__main__':
    process()