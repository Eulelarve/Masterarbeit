import cv2
from own_functions import insert, keep_rect_inside, valide_angle_zone
import settings as S
import numpy as np

class GUITile:
    def __init__(self, gui_object:object, name:str, image_path:str|None, type='GUITile'):
        self.parent:GuiOverlay = gui_object
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

    def select(self):
        self.selected = True

    def unselect(self):
        self.selected = False
        self.activated = False

    def pointer_selection(self, pointer_pos:tuple[int, int])->bool:
        if self.collide(pointer_pos):
            self.select()
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

    def set_center(self, pos:tuple[int,int]):
        x,y = pos
        _, _, w, h = self.rect
        self.rect[0] = x - w//2
        self.rect[1] = y - h//2

    def collide(self, pos:tuple[int,int]):
        if self.show:
            if self.rect is None:
                return None

            px, py = pos
            x, y, w, h = self.rect

            if x <= px <= x + w and y <= py <= y + h:
                return True
        return False
    
    @property
    def center(self):
        if self.rect is None:
            return None

        x, y, w, h = self.rect
        return (x + w // 2, y + h // 2)
    
    def remove(self):
        self.group.remove(self)

    def draw(self, frame):
        if self.show:
            if self.rect is None:
                self.update_rect(frame)
            if self.rect is None:
                return False
        
            edge = self.icon_farme_edge
            fh = frame.shape[0]
            fw = frame.shape[1]

            x, y, w, h = keep_rect_inside(self.rect,(fw,fh))
            
            self._adjust_icon()

            if edge:
                self.draw_icon_frame(frame, 2)

            overlay_image(frame,self.icon,(x +edge, y +edge))
            # frame[y +edge : y + h -edge , x +edge : x + w -edge ] = self.icon
        return True

    def update_rect(self, frame):
        raise "not implemented"
    
    def draw_icon_frame(self, frame, width):
        fh = frame.shape[0]
        fw = frame.shape[1]
        x, y, w, h = keep_rect_inside(self.rect,(fw,fh))
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

    def change_size_by(self, size_change:tuple|int):
        if self.rect:
            if type(size_change) is int:
                x = size_change
                y = size_change
            else:
                x,y = size_change
            self.rect[0] -= x//2
            self.rect[1] -= y//2
            self.rect[2] += x
            self.rect[3] += y
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
        if image_path:
            self.image = cv2.imread(image_path)
            if self.image.shape[2] == 3:
                self.image = cv2.cvtColor(self.image, cv2.COLOR_BGR2BGRA) # converte to imate with alpher cannle
            if self.image is None:
                self._create_image()
        elif self.image is None:
            self._create_image()

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
        
        self.icon = cv2.resize(self.image, new_size)
        return True # was shaped


class Instrument(GUITile):
    def __init__(self, gui_object:object, name:str, image_path:str|None):
        super().__init__(gui_object, name, image_path, S.type_instrument)
        self.bar_pos:int = None
        self.bar_rect:list = None
        self.elevation:float = None
        self.azimuth:float = None
        self.volume:float = S.instrument_start_volume
        self.on_off = 0

    def update_rect(self, rect):
        x,y,w,h = rect
        self.rect = [x,y,w,h]
        self.bar_rect = [x,y,w,h]
    
    def _create_image(self):
        size = 120
        name = self.name[:2].upper()
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

class VolumeBar(GUITile):
    def __init__(self ,gui_object:object, ):
        self.width_factor = 0.5  # halbe Bildbreite
        self.height_factor = 0.15
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
                instrument.volume = self.volume
            elif self.volume !=instrument.volume:
                self.change_volume(instrument.volume)
        
    def change_volume(self, new_volume):
        if self.volume != new_volume:
            self.volume = round(new_volume, S.volume_decimal_place)
            self._create_image()
            self._create_icon()

    def function(self):
        super().function()
        self.set_volume_from_position(self.parent.draw_pos)

    def _create_image(self):
        text = f"- : : : : : volume {self.volume:.2f} : : : : : +"
        super()._create_image(text)

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
        self.parent.add_info(self.get_info())



    
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
        self.parent.reset_instruments()

class ChangeVisibility(GUITile):
    def __init__(self, gui_object:object):
        name = 'show'
        type = 'ChangeVisibility'
        self.width_factor = 0.15
        self.height_factor = 0.1
        super().__init__(gui_object, name, None, type)
        self._function = 'show gui'
        self.modes = {0:'show buttons',1:'show gui', 2:'show gui and processing', 3:'show buttons and processing'}
        self.mode_counter = 1

    def function(self):
        super().function()
        self.next_mode()
        self.parent.set_gui_visibility(self._function)
        self.parent.add_info(self.get_info())

    def next_mode(self):
        self.mode_counter += 1
        nr = self.mode_counter % len(self.modes)
        self._function = self.modes[nr]
  
    def update_rect(self, frame):
        margin = 10
        fh, fw = frame.shape[:2]
        w = int(fw * self.width_factor)
        h = int(fh * self.height_factor)
        x = margin
        y = margin * 3

        self.rect = [x, y, w, h]

class InfoButton(GUITile):
    def __init__(self, gui_object:object):
        name = 'info'
        type = 'button'
        self.width_factor = 0.15
        self.height_factor = 0.1
        super().__init__(gui_object, name, None, type)

    def update_rect(self, frame):
        margin = 10
        fh, fw = frame.shape[:2]
        w = int(fw * self.width_factor)
        h = int(fh * self.height_factor)
        x = margin
        y = margin * 3
        self.rect = [x, y, w, h]

    def select(self):
        self.function()
        return super().select()

    def function(self):
        super().function()
        self.parent.show_info_menu = True

    
class GuiOverlay:
    def __init__(self, frame=None):
        self.frame = frame
        self.bar:list[Instrument] =[]
        self.room:list[Instrument] = []
        self.menu:list[GUITile] = []
        self.selected:GUITile|Instrument = None
        self.grabbing = False
        self.sel_size = 10
        self.room_size = -20
        self.draw_pos = None
        self.info_dict_list:list[dict] = []
        self.overlay_top_zone = None
        self.overlay_bot_zone = None
        self.in_room_zone = None
        self.info_menu_image = cv2.imread(S.gui_info_image_path, cv2.IMREAD_UNCHANGED)
        self.show_info_menu = False
        self.volume_bar = VolumeBar(self)
        # self.x = CloseButton(self)
        # self.reset_btn = ResetInstruments(self)
        # self.show = ChangeVisibility(self)
        self.info_btn = InfoButton(self)

        self.volume_bar.show = False
        self.menu.append(self.volume_bar)
        # self.menu.append(self.x)
        # self.menu.append(self.reset_btn)
        # self.menu.append(self.show)
        self.menu.append(self.info_btn)

    def add_instrument(self, name, image_path='', position=-1):
        instrument = Instrument(self, name, image_path)
        self._add_to_bar(instrument, position)
        self.define_bar_tile_pos_and_size()
    
    def _add_to_bar(self, instrument:Instrument, position:int=None):
        if instrument.bar_rect:
            instrument.rect = instrument.bar_rect.copy() # get the old bar position beck
        
        if instrument in self.room:
            self.room.remove(instrument)

        if position is None:
            position = instrument.bar_pos
        insert(self.bar, position, instrument)

    def _add_to_room(self, instrument:Instrument):
        if instrument in self.room:
            return False
        if instrument in self.bar:
            self.bar.remove(instrument)
        
        self.selected_size_change(self.room_size)
        self.room.append(instrument)

    def define_bar_tile_pos_and_size(self):
        tile_max_size = 120

        if not self.bar:
            return False
        if self.frame is None:
            return False

        margin = 10
        n = len(self.bar)

        tile_size = min(
            tile_max_size,
            (self.frame.shape[1] - margin * (n - 1)) // n,
        )
        w = n * (tile_size + margin) - margin 
        edge = (self.frame.shape[1] - w) // 2

        for i, inst in enumerate(self.bar):
            x = edge + i * (tile_size + margin)
            inst.update_rect([x, self.hight, tile_size, tile_size])
            inst.bar_pos = i
        
        return True
    
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
        self.room_top = int(self.frame.shape[0] * S.arm_decection_border_top)
        self.room_bot = int(self.frame.shape[0] * S.arm_decection_border_bot)
        self.create_border_zone_indicator()
        self.define_bar_tile_pos_and_size()
        x = int((self.frame.shape[1] - self.info_menu_image.shape[1])/2)
        y = int((self.frame.shape[0] - self.info_menu_image.shape[0])/2)
        self.info_menu_pos = x,y

    def draw(self, frame):
        if self.frame is not frame:
            self._set_frame(frame)

        if self.in_room_zone == False:
            overlay_image(self.frame,self.overlay_top_zone,(0, 0))
            y = self.frame.shape[0] - self.overlay_bot_zone.shape[0]
            overlay_image(self.frame,self.overlay_bot_zone,(0, y))

        if self.show_info_menu:
            overlay_image(self.frame, self.info_menu_image, self.info_menu_pos)
            self.show_info_menu = False
        else:
            for tile in [ *self.bar, *self.room, *self.menu,]:
                tile.draw(self.frame)

        if self.draw_pos is not None:
            cv2.circle(self.frame, self.draw_pos, 5, S.red, -1)
            self.draw_pos = None

        
    def select(self, pointer_pos:tuple[int,int]):
        self.draw_pos = pointer_pos[:] # copy th pointer/hand pos
        if self.grabbing:
            self.volume_bar.interaced_with_instrument(self.selected, pointer_pos) 
            self.in_room_zone = valide_angle_zone(pointer_pos, self.frame.shape)
            if self.in_room_zone:
                self.show_valume_bar(True)

            return self.selected
        else: 
            self.selected = None

            for tile in  [*self.bar, *self.room, *self.menu]:

                if tile.pointer_selection(pointer_pos):
                    self.selected = tile
                    return tile
        return None
    
    def show_valume_bar(self, show:bool):
        if self.volume_bar.show == show:
            return
        self.show_instrument_bar(not show)
        self.volume_bar.show = show

    def show_instrument_bar(self, show:bool):
        for inst in self.bar:
            if inst is self.selected:
                continue
            inst.show = show
    
    def set_gui_visibility(self, mode:str):
        show_all = 'gui' in mode
        for tile in [ *self.bar, *self.room, *self.menu,]:
                    tile.show = show_all
        if 'button' in mode:
            self.info_btn.show = True 
        self.volume_bar.show = False

    def grap(self):
        if self.selected is None:
            return False
        if self.grabbing == False:
            if type(self.selected) is Instrument:
                # self.reset_btn.show = False
                self._set_grap_mode(True)
                self.selected.turn_on()

            elif self.selected in self.menu:
                self.selected.function()

        return True
    
    def selected_size_change(self, size_change:int):
        self.selected.change_size_by(size_change)

    def reset_instruments(self):
        for inst in self.bar:
            inst.volume = S.instrument_start_volume
        self.clear_room()
        # self.reset_btn.show = False

    def clear_room(self,):
        for inst in self.room.copy():
            inst.reset()
            self._add_to_bar(inst)
            self.add_info(inst.get_info())

    def _set_grap_mode(self, on:bool):
        if self.grabbing != on:
            self.grabbing = on
            # self.x.show = not on
            self.info_btn.show = not on
            self.selected.activated = on
            if self.selected in self.bar:
                self.selected_size_change(self.sel_size * (1-2*on))
            elif self.selected in self.room:
                self.selected_size_change(self.sel_size* -(1-2*on))

    def release(self, )->bool:
        if self.selected is None:
            return False
        
        if self.grabbing:
            if valide_angle_zone(self.selected.center, self.frame.shape):
                self._add_to_room(self.selected)
            else:
                self._add_to_bar(self.selected, True)
                self.selected.turn_off()
                self.selected.set_angle(None, None)
                self.add_info(self.selected.get_info())

            self.in_room_zone = None
            self.show_valume_bar(False)

            # if self.room or [inst for inst in self.bar if inst.volume != S.instrument_start_volume]:
            #     self.reset_btn.show = True
            # else:
            #     self.reset_btn.show = False

            self._set_grap_mode(False)
        return True

    def move(self, pos:tuple[int,int], azimuth:float=None, elevation:float=None,)-> bool:
        if not self.grabbing:
            return False
        self.selected.set_angle(azimuth=azimuth, elevation=elevation)
        self.selected.set_center(pos)
        self.add_info(self.selected.get_info())


        return True

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


def cv2_create_text_image(text:str, size:tuple[int,int]|int=100, back_ground_color = (0, 0, 0, 100), text_color=(255,255,255,255), line_size=4, text_outline=1):
        if type(size) is int:
            x = size
            y = size
        else:
            x,y = size
        if len(back_ground_color) != 4:
            raise "back_ground_color must be a tuple of 4 ... BGRA"
        img = np.full((y, x, 4), back_ground_color, np.uint8)
        cv2_set_fitting_text(img, text, text_color,text_outline,line_size)
        return img

def cv2_set_fitting_text(img, text:str, color=(255,255,255,255), outlined=1, line_size = 4,margin = 10,):
    if len(color) != 4:
            raise "color must be a tuple of 4 ... BGRA"
    color_outline = (0,0,0,255)

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

    # Vertikal zentrieren (Baseline beachten!)
    y = (h + text_h) // 2
    if outlined:
        cv2.putText(
            img,
            text,
            (x, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            color_outline,
            line_size+2*outlined,
            cv2.LINE_AA,
            )

    cv2.putText(
        img,
        text,
        (x, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        color,
        line_size,
        cv2.LINE_AA,
        )


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

    roi = frame[y1:y2, x1:x2]

    # Alpha-Kanal
    alpha = overlay_crop[:, :, 3:4] / 255.0

    # Alpha-Blending
    roi[:] = (
        alpha * overlay_crop[:, :, :3] +
        (1.0 - alpha) * roi
    ).astype(np.uint8)