import cv2
from own_functions import insert, keep_rect_inside, fit_in_frame, make_image_fit_in_rect, cv2_draw_dict, cv2_putText_outlined, point_rect_collision, pos_in_frame
from analyse import find_files
import settings as S
import numpy as np
import math

class GUITile:
    def __init__(self, gui_object:object, name:str, image_path:str|None, type='GUITile'):
        self.gui:GuiOverlay = gui_object
        self.si:int = None
        self.type = type
        self.name = name
        self.icon = None
        self.image = None
        self.show = True
        self.rect:list = None
        self.info_dict = {}
        self.selected = False
        self.activated = False
        self._function = 'no function'

        self.icon_farme_edge = 4

        self.set_image(image_path)
        self._adjust_icon()

    def select(self, selector_index:int):
        self.selected = True
        self.si = selector_index

    def unselect(self):
        self.selected = False
        self.activated = False
        if self.si is not None:
            self.gui.grabbing[self.si] = False
            self.gui.selected[self.si] = None
            self.si = None

    def pointer_selection(self, pointer_pos:tuple[int, int], selector_index:int)->bool:
        if self.collide(pointer_pos):
            self.select(selector_index)
            return True
        self.unselect()
        return False

    def get_info(self):
        self.info_dict['name'] = self.name
        self.info_dict['type'] = self.type
        self.info_dict['function'] = self._function
        return self.info_dict.copy()
    
    def function(self):
        self.activated = True

    def set_center(self, pos:tuple[int,int], keep_in_frame=False):
        x,y = pos
        _, _, w, h = self.rect
        self.rect[0] = x - w//2
        self.rect[1] = y - h//2
        if keep_in_frame:
            fh,fw = self.gui.frame.shape[:2]
            self.rect = keep_rect_inside(self.rect,(fw,fh))

    def collide(self, pos:tuple[int,int]):
        if self.show:
            if self.rect is None:
                return None
            return point_rect_collision(pos, self.rect)
        return False
    
    @property
    def center(self):
        if self.rect is None:
            return None

        x, y, w, h = self.rect
        return (x + w // 2, y + h // 2)
    
    def remove(self):
        self.group.remove(self)

    def draw(self, frame, show_info_dict = False):
        if self.show:
            if self.rect is None:
                self.update_rect(frame)
            if self.rect is None:
                return False
        
            edge = self.icon_farme_edge
            x, y, w, h = self.rect    
            self._adjust_icon()
            if edge:
                self.draw_icon_frame(frame, 2)

            overlay_image(frame,self.icon,(x +edge, y +edge))
            # frame[y +edge : y + h -edge , x +edge : x + w -edge ] = self.icon
            if show_info_dict:
                cv2_draw_dict(frame, self.info_dict, (x+w+10,y), font_size=0.5, line_size=1, outlined=1, color=S.white)
        return True

    def update_rect(self, frame):
        raise "not implemented"
    
    def draw_icon_frame(self, frame, width):
        x, y, w, h = self.rect
        color1 = S.white
        color2 = S.black

        if self.activated:
            color1 = S.red
            color2 = S.red
        elif self.selected:
            color1 = S.yellow
            color2 = S.yellow

        cv2.rectangle(frame, (x, y), (x+w, y+h), color1, width)
        cv2.rectangle(frame, (x , y), (x+w, y+h), color2, 1)

    def resize(self, new_size:tuple|int):
        """ 
            change the size but keep the center position
        """
        if self.rect:
            if type(new_size) is int:
                w = new_size
                h = new_size
            else:
                w,h = new_size
            dx = w-self.rect[2]
            dy = h-self.rect[3]
            self.rect[0] -= dx//2
            self.rect[1] -= dy//2
            self.rect[2] += dx
            self.rect[3] += dy
            return True
        return False
    
    def _create_image(self,text:str=None, back_ground_color=(0,0,0,100), text_color=(255,255,255,255),line_size=4,text_outline=1):
        if self.rect:
            _, _, w, h = self.rect
            w -= self.icon_farme_edge*2
            h -= self.icon_farme_edge*2
            if text is None:
                text = self.name
            self.image = cv2_create_text_image(text, (w,h), back_ground_color, text_color,line_size,text_outline)
    
    def set_image(self, image_path:str|None):
        if not image_path:
            image_path = self._find_image()
        if image_path:
            self.image = cv2.imread(image_path)
            if self.image is None:
                self.image = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)                   
            if self.image.shape[2] == 3:
                self.image = cv2.cvtColor(self.image, cv2.COLOR_BGR2BGRA) # converte to image with alpher cannle
        if self.image is None:
            self._create_image()

    def _find_image(self):
        folder = "../icons/"
        name = self.name.replace("-", "").replace(" ", "")
        name = name.lower()
        path_list = find_files(folder=folder,contains=name, names_only=False)
        if path_list:
            return path_list[0]
        return None

    def _adjust_icon(self):
        if self.rect is None:
            return False # not posible
        if self.image is None:
            self._create_image() # try to create one
        if self.image is None:
            return False # not posible
        edge = self.icon_farme_edge
        w, h = self.rect[2:]
        new_size = w - 2* edge, h -2* edge

        if self.icon is not None:
            if self.icon.shape[1] == new_size[0] and self.icon.shape[0] == new_size[1]: # if x = x_new and y =  y_new
                return True # shape allready right sized
        
        self._create_icon()

    def _create_icon(self):
        edge = self.icon_farme_edge
        w, h = self.rect[2:]
        new_size = w - 2* edge, h -2* edge
        self.icon = np.ones((*new_size[::-1], 4), dtype=np.uint8) * 255
        image = make_image_fit_in_rect(self.image, new_size)
        pos = int((new_size[0]-image.shape[1])/2), int((new_size[1]-image.shape[0])/2)
        overlay_image(self.icon, image, pos)
        return True # was shaped


class Instrument(GUITile):
    def __init__(self, gui_object:object, name:str, image_path:str|None):
        super().__init__(gui_object, name, image_path, S.type_instrument)
        self.bar_pos:int = None
        self.rect_bar:list = None
        self.elevation:float = None
        self.azimuth:float = None
        self.volume:float = S.instrument_start_volume
        self.on_off = 0

    def select(self, selector_index):
        super().select(selector_index)
        if not self.gui.volume_bar in self.gui.selected:
            self.gui.volume_bar.change_volume(self.volume)

    def change_volume(self, volume:float):
        self.volume = volume
        self.gui.add_info(self.get_info())

    def update_rect(self, rect):
        x,y,w,h = rect
        self.rect = [x,y,w,h]
        self.rect_bar = [x,y,w,h]
    
    def _create_image(self):
        size = 120
        name = self.name[:4].upper()
        self.image = cv2_create_text_image(name, size)

    def get_info(self):
        self.info_dict['azimuth'] = self.azimuth
        self.info_dict['elevation'] = self.elevation
        self.info_dict['volume'] = self.volume
        self.info_dict['on_off'] = self.on_off
        return super().get_info()

    def set_angle(self, azimuth:int|None, elevation:int|None):
        self.azimuth = azimuth
        self.elevation = elevation

    def turn_on(self):
        self.on_off = 1

    def turn_off(self):
        self.on_off = 0

    def reset(self):
        self.turn_off()
        self.set_angle(None, None)
        self.volume = S.instrument_start_volume

    def set(self, on_off:int, azimuth:int|None, elevation:int|None, volue:float):
        self.on_off = on_off
        self.set_angle(azimuth, elevation)
        self.volume = volue

class InstrumentSelection(GUITile):
    def __init__(self, gui_object):
        self.pos = 0.5, 0.85
        self.size = S.gui_tile_max_size
        name = 'instrument_selection_button'
        type = 'button'
        super().__init__(gui_object, name, None, type)

    def select(self, selector_index:int):
        super().select(selector_index)
        if not self.gui.bar_rect:
            # selgection menu/bar is closed... so open it now
            self.gui.show_selection(True)

    def update_rect(self, frame):
        fh, fw = frame.shape[:2]
        w = self.size
        h = w
        x = int(self.pos[0] * fw -w/2)
        y = int(self.pos[1] * fh -h/2)
        self.rect = [x,y,h,w]

    def set_center(self, pos, keep_in_frame=True):
        super().set_center(pos, keep_in_frame)
        self.gui.bar_rect = self.gui.define_selecton_bar()
        # self.gui.volume_bar.set_center(pos, keep_in_frame)

class VolumeBar(GUITile):
    def __init__(self ,gui_object:object, ):
        self.width_factor = 0.25  # part of the screen
        self.height_factor = 0.09
        name = "volume"
        self.volume = 0.0
        super().__init__(gui_object, name, None, 'VolumeBar')
        self._function = "change volume"

    def get_info(self):
        self.info_dict['volume'] = self.volume
        return super().get_info()

    def update_rect(self, frame):
        fh, fw = frame.shape[:2]

        w = int(fw * self.width_factor)
        h = int(fh * self.height_factor)
        x = (fw - w) // 2
        # y = int(fh * S.gui_hight -h )
        y = int(fh * (1 - S.gui_hight))

        self.rect = [x, y, w, h]

    def select(self, selector_index):
        super().select(selector_index)
        pos = self.gui.pointer_pos[selector_index]
        for tile in self.gui.selected:
            if type(tile) is Instrument:
                self.set_volume_from_position(pos)
                tile.change_volume(self.volume)

    
    def set_volume_from_position(self, pos:tuple[int,int])->float:
        """Setzt den Lautstärkewert anhand einer Bildkoordinate."""
        px, _ = pos
        x, _, w, _ = self.rect
        value = (px - x) / w
        value = max(0.0, min(1.0, value))
        self.change_volume(value)

    def interaced_with_instrument(self, instrument:Instrument, pos:tuple[int,int]):
        if self.show:
            self.selected = False
            if self.collide(pos):
                self.selected = True
                self.set_volume_from_position(pos)
                instrument.change_volume(self.volume)
        
    def change_volume(self, new_volume):
        if self.volume != new_volume:
            self.volume = round(new_volume, S.volume_decimal_place)
            self._create_image()
            self._create_icon()

    def _create_image(self):
        text = f"- : : : : volume {self.volume:.2f} : : : : +"
        super()._create_image(text,S.green, line_size=2)

class CloseButton(GUITile):
    def __init__(self, gui_object:object):
        name = 'X'
        super().__init__(gui_object, name, None, 'CloseButton')
        self._function = 'close application'

    def update_rect(self, frame):
        margin = 10
        w = 120
        h = 120
        x = int(frame.shape[1] - w - margin)
        y = margin
        self.rect = [x,y,w,h]

    def _create_image(self,):
        return super()._create_image(back_ground_color=(*S.red, 50))

    def function(self):
        super().function()
        self.gui.add_info(self.get_info())

    
class ResetInstruments(GUITile):
    def __init__(self, gui_object:object):
        self.width_factor = 0.2 
        self.height_factor = 0.1
        name = 'reset Instruments'
        type = 'ResetInstruments'
        super().__init__(gui_object, name, None, type)
        self.show = False # not viseble at the programm start
        self._function = 'reset instruments'

    def _create_image(self):
        return super()._create_image(line_size=2)
    
    def update_rect(self, frame):
        margin = 10
        fh, fw = frame.shape[:2]
        w = int(fw * self.width_factor)
        h = int(fh * self.height_factor)
        x = (fw - w) // 2
        y = margin

        self.rect = [x, y, w, h]

    def function(self):
        super().function()
        self.gui.reset_instruments()

# class ChangeVisibility(GUITile):
#     def __init__(self, gui_object:object):
#         name = 'show'
#         type = 'ChangeVisibility'
#         self.width_factor = 0.15
#         self.height_factor = 0.1
#         super().__init__(gui_object, name, None, type)
#         self._function = 'show gui'
#         self.modes = {0:'show buttons',1:'show gui', 2:'show gui and processing', 3:'show buttons and processing'}
#         self.mode_counter = 1

#     def function(self):
#         super().function()
#         self.next_mode()
#         self.gui.set_gui_visibility(self._function)
#         self.gui.add_info(self.get_info())

#     def next_mode(self):
#         self.mode_counter += 1
#         nr = self.mode_counter % len(self.modes)
#         self._function = self.modes[nr]
  
#     def update_rect(self, frame):
#         margin = 10
#         fh, fw = frame.shape[:2]
#         w = int(fw * self.width_factor)
#         h = int(fh * self.height_factor)
#         x = margin
#         y = margin * 3

#         self.rect = [x, y, w, h]

class InfoButton(GUITile):
    def __init__(self, gui_object:object):
        name = 'info_button'
        type = 'button'
        self.size_factor = 0.2
        super().__init__(gui_object, name, None, type)

    def update_rect(self, frame):
        margin = 10
        fh, fw = frame.shape[:2]
        h = int(fh * self.size_factor)
        if self.image is None:
            w = int(fw *self.size_factor)
        else:
            ih, iw = self.image.shape[:2]
            w = int(iw / ih * h)
        x = fw - w - margin
        y = margin
        self.rect = [x, y, w, h]

    def select(self, selector_index:int):
        self.function()
        return super().select(selector_index)

    def function(self):
        super().function()
        self.gui.show_info_menu = True

    
class GuiOverlay:
    def __init__(self, frame=None):
        self.frame = frame
        self.bar:list[Instrument] =[]
        self.room:list[Instrument] = []
        self.menu:list[GUITile] = []
        self.selected:list[GUITile|Instrument|None] = [None, None, None]
        self.grabbing:list[bool] = [False, False, False]
        self.sel_tile_size = []
        self.room_tile_size = []
        self.bar_tile_size = []
        self.pointer_pos:list[tuple, tuple, tuple] = [None, None, None]
        self.info_dict_list:list[dict] = []
        self.overlay_top_zone = None
        self.overlay_bot_zone = None
        self.in_room_zone = None
        self.bar_rect:tuple = None
        self.info_menu_image = cv2.imread(S.gui_info_image_path, cv2.IMREAD_UNCHANGED)
        self.show_info_menu = False
        self.volume_bar = VolumeBar(self)
        # self.x = CloseButton(self)
        # self.reset_btn = ResetInstruments(self)
        # self.show = ChangeVisibility(self)
        self.info_btn = InfoButton(self)
        self.selection_btn = InstrumentSelection(self)

        self.volume_bar.show = False
        self.menu.append(self.volume_bar)
        # self.menu.append(self.x)
        # self.menu.append(self.reset_btn)
        # self.menu.append(self.show)
        self.menu.append(self.info_btn)
        self.menu.append(self.selection_btn)

        self.define_tile_sizes()

    def add_instrument(self, name, image_path='', position=-1):
        instrument = Instrument(self, name, image_path)
        self._add_to_bar(instrument, position)
    
    def _add_to_bar(self, instrument:Instrument, position:int=None):
        if instrument.rect_bar:
            instrument.rect = instrument.rect_bar.copy() # get the old bar position beck
        instrument.resize(self.bar_tile_size)
        if instrument in self.room:
            self.room.remove(instrument)
        if instrument not in self.bar:
            insert(self.bar, 
                   instrument.bar_pos if position is None else position, 
                   instrument)

    def _add_to_room(self, instrument:Instrument):
        instrument.resize(self.room_tile_size)
        if instrument in self.room:
            return False
        if instrument in self.bar:
            self.bar.remove(instrument)
        if instrument not in self.room:
            self.room.append(instrument)

    def show_selection(self, show):
        if show:
            self.bar_rect = self.define_selecton_bar()
        else:
            self.bar_rect = None
        self.show_bar_instrument(show)
        # self.show_room_instrument(not show)

    def define_tile_sizes(self):
        selected_tile_size_factor = 0.85
        room_tile_size_factor = 0.7
        tile_size = S.gui_tile_max_size
        self.bar_tile_size = int(tile_size), int(tile_size)
        self.room_tile_size = int(tile_size *room_tile_size_factor),  int(tile_size *room_tile_size_factor)
        self.sel_tile_size = int(tile_size *selected_tile_size_factor),  int(tile_size *selected_tile_size_factor)

    def define_selecton_bar(self):
        if not self.bar:
            return None
        if self.frame is None:
            return None
        margin = 10
        n = len(self.bar) + 1
        rows = int(n**0.5)
        cols = math.ceil(n/rows)
        dx = self.bar_tile_size[0] + margin
        dy = self.bar_tile_size[1] + margin
        sel_pos = self.selection_btn.rect[:2]
        start_x = sel_pos[0] - (cols-1)//2 * dx
        start_y = sel_pos[1] 
        slots = []
        for row in range(rows):
            y = start_y - row * dy
            for col in range(cols):
                x = start_x + col * dx
                if [x,y] != sel_pos:
                    slots.append([x,y])
        bar_rect = (start_x, y , cols * dx , rows * dy)
        for i, inst in enumerate(self.bar):
            inst.update_rect([*slots[i], *self.bar_tile_size])
            inst.bar_pos = i
        return bar_rect
    
    def _set_frame(self, frame):
        if self.frame is None:
            self._set_frame_and_dependencies(frame)
        else:
            if frame.shape != self.frame.shape:
                self._set_frame_and_dependencies(frame)
            else:
                self.frame = frame
    
    def _set_frame_and_dependencies(self, frame):
        self.frame = frame
        self.hight = int(self.frame.shape[0] * (1 - S.gui_hight))
        # self.create_border_zone_indicator()
        self.init_menu_rects()
        self.define_selecton_bar()

    def init_menu_rects(self):
        for tile in self.menu:
            tile.update_rect(self.frame)
        self.volume_bar.set_center(self.selection_btn.center)

    def calc_info_image_pos(self, frame):
        x = int((frame.shape[1] - self.info_menu_image.shape[1])/2)
        y = int((frame.shape[0] - self.info_menu_image.shape[0])/2)
        x = max(x,0)
        y = max(y,0)
        self.info_menu_pos = x, y 

    def draw(self, frame, show_processing):
        if self.frame is not frame:
            self._set_frame(frame)

        if self.in_room_zone == False:
            overlay_image(self.frame,self.overlay_top_zone,(0, 0))
            y = self.frame.shape[0] - self.overlay_bot_zone.shape[0]
            overlay_image(self.frame,self.overlay_bot_zone,(0, y))

        if self.show_info_menu:
            self.info_menu_image = fit_in_frame(self.frame, self.info_menu_image, 10)
            self.calc_info_image_pos(self.frame)
            overlay_image(self.frame, self.info_menu_image, self.info_menu_pos)
        else:
            for tile in [*self.room, *self.bar,  *self.menu,]:
                show_infos = show_processing and tile in self.room
                tile.draw(self.frame, show_infos)

        for pos in self.pointer_pos: 
            if not pos:
                continue
            cv2.circle(self.frame, pos, 5, S.red, -1)

    def pos_in_bar_zoon(self, pos):
        if not self.bar_rect:
            return None
        return point_rect_collision(pos, self.bar_rect)

    def any_pos_in_bar_zoon(self)->bool:
        for pos in self.pointer_pos:
            if pos:
                if self.pos_in_bar_zoon(pos):
                    return True
        return False

    def pointer_in_reset_zoon(self,i:int)->bool:
        pos = self.pointer_pos[i]
        if not pos:
            return False
        if self.pos_in_bar_zoon(pos):
            return True
        # if self.volume_bar.collide(pos):
        #     return True
        if self.selection_btn.collide(pos):
            return True
        if self.frame is not None: 
            if not pos_in_frame(pos, self.frame):
                # instrument out of screen
                return True
        return False
        
    def select(self, hand_pos1:tuple[int,int],hand_pos2:tuple[int,int],mouse_pos:tuple[int,int]):
        self.pointer_pos = [() if pos is None else tuple(pos) for pos in (hand_pos1, hand_pos2, mouse_pos)]
        if self.any_pos_in_bar_zoon() == False:
            self.show_selection(False)
        if not self.instrument_is_selected():
            self.show_volume_bar(False)
        for i in range(3):
            pos = self.pointer_pos[i]
            if not pos:
                continue
            if self.grabbing[i]:
                if type(self.selected[i]) is Instrument:
                    self.volume_bar.interaced_with_instrument(self.selected[i], pos) 
            else: 
                self.selected[i] = None
                for tile in  [*self.bar, *self.room, *self.menu]:
                    if not tile in self.selected:
                        if tile.pointer_selection(pos,i):
                            self.selected[i] = tile
                            if tile in self.room:
                                self.show_volume_bar(True)

    def instrument_is_selected(self):
        for tile in self.selected:
            if type(tile) is Instrument:
                return True
        return False

    def show_bar_instrument(self, show:bool):
        for inst in self.bar:
            if inst in self.selected:
                continue
            inst.show = show

    def show_room_instrument(self, show:bool):
        for inst in self.room:
            if inst in self.selected:
                continue
            inst.show = show

    def show_volume_bar(self, show:bool):
        if show != self.volume_bar.show:
            self.volume_bar.show = show
            self.selection_btn.show = not show
            if show:
                self.show_selection(False)
                if self.selection_btn in self.selected:
                    self.selection_btn.unselect()

    def set_gui_visibility(self, mode:str):
        print('set GUI visibility mode to ',mode)
        show_all = 'gui' in mode
        for tile in [ *self.bar, *self.room, *self.menu,]:
                    tile.show = show_all
        if 'button' in mode:
            self.info_btn.show = True 
        self.volume_bar.show = False

    def grab(self,grab_hand1:bool, grab_hand2:bool, mouse_down:bool):
        for i, grab in enumerate([grab_hand1, grab_hand2, mouse_down]):
            selected = self.selected[i]
            if not grab or selected is None:
                continue
            if self.grabbing[i] == False:
                if type(selected) is Instrument:
                    # self.reset_btn.show = False
                    self._set_grab_mode(True,i)
                    selected.turn_on()
                    selected.resize(self.sel_tile_size)
                    self.show_volume_bar(True)
                elif selected in self.menu:
                    selected.function()
                    if type(selected) in [InstrumentSelection, VolumeBar]:
                        self._set_grab_mode(True,i)

    def reset_instruments(self):
        if not True in self.grabbing:
            print('reset all instruments')
            for inst in self.bar:
                inst.volume = S.instrument_start_volume
            self.clear_room()

    def reset_menu(self):
        if not True in self.grabbing:
            print('reset all menu elements')
            self.show_info_menu = False
            for tile in self.menu:
                tile.update_rect(self.frame)

    def reset_gui(self):
        self.reset_menu()
        self.reset_instruments()

    def clear_room(self,):
        for inst in self.room.copy():
            inst.reset()
            self._add_to_bar(inst)
            self.add_info(inst.get_info())

    def _set_grab_mode(self, on:bool, i:int):
        if self.grabbing[i] != on:
            self.grabbing[i] = on
            # self.x.show = not on
            self.info_btn.show = not on
            self.selected[i].activated = on

    def release(self,rel_hand1:bool, rel_hand2:bool, mouse_up:bool):
        for i, rel in enumerate([rel_hand1, rel_hand2, mouse_up]):
            if not rel:
                continue
            self.release_one(i)

    def release_one(self, i:int):
        selected = self.selected[i]
        if selected is None:
            return
        if self.grabbing[i]:
            if type(selected) is Instrument:
                if self.pointer_in_reset_zoon(i):
                    selected.show = False
                    self._add_to_bar(selected, True)
                    selected.turn_off()
                    selected.set_angle(None, None)
                    self.add_info(selected.get_info())
                else:
                    self._add_to_room(selected)
            self._set_grab_mode(False,i)
            # if not True in self.grabbing:
            #     self.show_volume_bar(False)



    def move(self, azimuth:tuple[float] = [None,None], elevation:tuple[float]=[None, None]):
        for i in range(3):
            if not self.grabbing[i]:
                continue
            pos = self.pointer_pos[i]
            selected = self.selected[i]
            selected.set_center(pos)
            if type(selected) is Instrument:
                if not pos_in_frame(pos, self.frame):
                    self.release_one(i)
                if i in [0,1]:
                    # angle is not for mouse interaction
                    selected.set_angle(azimuth=azimuth[i], elevation=elevation[i])
                self.add_info(selected.get_info())


    def create_border_zone_indicator(self):
        color = (*S.red, 30)
        x = self.frame.shape[1]
        y = self.frame.shape[0]
        top_border = int(S.arm_decection_border_top * y) 
        bot_border = int(S.arm_decection_border_bot * y) 
        self.overlay_top_zone = np.full((top_border, x, 4), color, dtype=np.uint8)
        self.overlay_bot_zone = np.full((y - bot_border, x, 4), color, dtype=np.uint8)

    def get_info(self):
        if self.info_dict_list:
            return self.info_dict_list.pop(0)
        return None

    def add_info(self, info_dict):
        self.info_dict_list.append(info_dict)


def cv2_create_text_image(text:str, size:tuple[int,int]|int=100, back_ground_color = (0, 0, 0, 100), text_color=(255,255,255,255), line_size=4, text_outline=2):
        if type(size) is int:
            x = size
            y = size
        else:
            x,y = size
        if len(back_ground_color) < 4:
            back_ground_color = (*back_ground_color, 255)
        img = np.full((y, x, 4), back_ground_color, np.uint8)
        cv2_set_fitting_text(img, text, text_color,text_outline,line_size)
        return img

def cv2_set_fitting_text(img, text:str, color=(255,255,255,255), outlined=2, line_size = 4, margin = 10,):
    h, w = img.shape[:2]

    # Textbreite bei fontScale=1 bestimmen
    (text_w, text_h), baseline = cv2.getTextSize(
        text,
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        2
    )

    # Schrift so skalieren, dass sie fast die gesamte Breite nutzt
    font_scale = (w - 2 * margin) / text_w

    # Neue Textgröße bestimmen
    (text_w, text_h), baseline = cv2.getTextSize(
        text,
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        2
    )

    x = margin
    y = (h + text_h) // 2
    # Vertikal zentrieren (Baseline beachten!)
    return cv2_putText_outlined(img=img,pos=(x,y),text=text,font_scale=font_scale,line_size=line_size,color=color, outlined=outlined)


def overlay_image(frame: np.ndarray, overlay: np.ndarray, pos: tuple[int, int]):
    """
    Blendet ein BGRA-Bild auf ein BGR-Bild.

    Parameters
    ----------
    frame : np.ndarray
        Zielbild (BGR)
    overlay : np.ndarray
        Bild mit Alpha-Kanal (BGRA)
    pos : tuple[int, int]
        (x, y) = linke obere Ecke im Zielbild
    """

    x, y = pos
    h, w = overlay.shape[:2]

    # Liegt das Overlay komplett außerhalb?
    if x >= frame.shape[1] or y >= frame.shape[0]:
        return
    if x + w <= 0 or y + h <= 0:
        return

    # Zuschneiden, falls es über den Rand hinausragt
    x1 = max(x, 0)
    y1 = max(y, 0)
    x2 = min(x + w, frame.shape[1])
    y2 = min(y + h, frame.shape[0])

    overlay_crop = overlay[
        y1 - y:y2 - y,
        x1 - x:x2 - x
    ]

    roi = frame[y1:y2, x1:x2, :3]

    # Alpha-Kanal
    alpha = overlay_crop[:, :, 3:4] / 255.0

    # Alpha-Blending
    roi[:] = (
        alpha * overlay_crop[:, :, :3] +
        (1.0 - alpha) * roi
    ).astype(np.uint8)

def pos_is_frame_boarder(pos:tuple[int, int], frame)->bool:
    h,w = frame.shape[:2]
    x,y = pos
    if 0 in pos:
        return True
    if x == w or y == h:
        return True
    return False