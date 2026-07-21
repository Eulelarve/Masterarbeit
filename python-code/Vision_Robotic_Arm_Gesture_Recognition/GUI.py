import cv2
from own_functions import insert, keep_rect_inside, valide_angle_area
import settings as S
import numpy as np

class GUITile:
    def __init__(self, name:str, image_path:str|None, type='GUITile'):
        self.type = type
        self.name = name
        self.icon = None
        self.image = None
        self.show = True
        self.rect:list = None
        self.info_dict = {}
        self.selected = False

        self.icon_farme_edge = 4

        self.set_image(image_path)
        self._adjust_icon()

    def get_info(self):
        self.info_dict['name'] = self.name
        self.info_dict['type'] = self.type
        return self.info_dict.copy()
    
    def function(self):
        raise "not implemented"

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
        color1 = S.yellow if self.selected else S.white
        color2 = S.yellow if self.selected else S.black
        cv2.rectangle(frame, (x, y), (x+w, y+h), color1, width)
        # adding smal black frame
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
    def __init__(self, name:str, image_path:str|None):
        super().__init__(name, image_path, S.type_instrument)
        self.bar_pos:int = None
        self.bar_rect:list = None
        self.elevation:float = None
        self.azimuth:float = None
        self.volume:float = S.instrument_start_volume

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
        self.info_dict['volume'] = self.volume
        return super().get_info()

class VolumeBar(GUITile):
    def __init__(self):
        self.width_factor = 0.5  # halbe Bildbreite
        self.height = 70
        name = "volume"
        self.volume = 0.0
        super().__init__(name, None, 'VolumeBar')

    def get_info(self):
        self.info_dict['volume'] = self.volume
        return super().get_info()

    def update_rect(self, frame):
        fh, fw = frame.shape[:2]

        w = int(fw * self.width_factor)
        h = self.height
        x = (fw - w) // 2
        y = int(fh * S.gui_hight - self.height)

        self.rect = [x, y, w, h]

    def set_volume_from_position(self, pos:tuple[int,int])->float:
        """Setzt den Lautstärkewert anhand einer Bildkoordinate."""
        px, _ = pos
        x, _, w, _ = self.rect
        value = (px - x) / w
        value = max(0.0, min(1.0, value))
        self.change_volume(value)

    def interaced_with_instrument(self, instrument:Instrument, pos:tuple[int,int]):
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
        
    def _create_image(self):
        text = f"- : : : : : volume {self.volume:.2f} : : : : : +"
        super()._create_image(text)

class CloseButton(GUITile):
    def __init__(self,):
        name = 'X'
        super().__init__(name, None, 'CloseButton')

    def update_rect(self, frame):
        margin = 10
        w = 120
        h = 120
        x = int(frame.shape[1] - w - margin)
        y = margin
        self.rect = [x,y,w,h]

    def _create_image(self,):
        return super()._create_image(back_ground_color=(*S.red, 50))

class ResetInstruments(GUITile):
    def __init__(self):
        self.width_factor = 0.2 
        self.height = 50
        name = 'reset Instruments'
        type = 'ResetInstruments'
        super().__init__(name, None, type)
        self.show = False # not viseble at the programm start

    def _create_image(self):
        return super()._create_image(line_size=2)
    
    def update_rect(self, frame):
        margin = 20
        fh, fw = frame.shape[:2]
        w = int(fw * self.width_factor)
        h = self.height
        x = (fw - w) // 2
        y = margin

        self.rect = [x, y, w, h]

class GuiOverlay:

    def __init__(self, frame=None):
        self.frame = frame
        self.bar:list[Instrument] =[]
        self.room:list[Instrument] = []
        self.menu:list[GUITile] = []
        self.selected:GUITile = None
        self.grasped = False
        self.sel_size = 10
        self.room_size = -30
        self.draw_pos = None
        self.info_dict = {}
        self.volume_bar = VolumeBar()
        self.x = CloseButton()
        self.reset_btn = ResetInstruments()

        self.volume_bar.show = False
        self.menu.append(self.volume_bar)
        self.menu.append(self.x)
        self.menu.append(self.reset_btn)

    def add_instrument(self, name, image_path='', position=-1):
        instrument = Instrument(name, image_path)
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
        self.define_bar_tile_pos_and_size()

    def draw(self, frame):
        if self.frame is not frame:
            self._set_frame(frame)

        for inst in [ *self.bar, *self.room, *self.menu,]:
            inst.draw(self.frame)
        
        if self.draw_pos:
            cv2.circle(frame, self.draw_pos, 5, S.red, -1)
        
    def select(self, pointer_pos:tuple[int,int]):
        self.draw_pos = None
        if self.grasped:
            self.volume_bar.interaced_with_instrument(self.selected, pointer_pos) 
            if self.volume_bar.collide(pointer_pos):
                self.draw_pos = pointer_pos[:] # copy pos
            return self.selected
        else: 
            self.selected = None

            for tile in  [*self.bar, *self.room, *self.menu]:

                tile.selected = False

                if tile.collide(pointer_pos):
                    self.draw_pos = pointer_pos[:] # copy pos
                    tile.selected = True
                    self.selected = tile
                    return tile
        
        return None
    
    def grap(self):
        if self.selected is None:
            return False
        if self.grasped == False:
            if type(self.selected) is Instrument:
                self._set_grap_mode(True)

            if self.selected in self.bar:
                self.selected_size_change(-self.sel_size)
            elif self.selected in self.room:
                self.selected_size_change(self.sel_size)

            elif self.selected in self.menu:
                self.info_dict = self.selected.get_info()
                if type(self.selected) is ResetInstruments:
                    self.reset_instruments()

        return True
    
    def selected_size_change(self, size_change:int):
        self.selected.change_size_by(size_change)

    def reset_instruments(self):
        for inst in [*self.room, *self.bar]:
            inst.volume = S.instrument_start_volume
        self.clear_room()
        self.reset_btn.show = False

    def clear_room(self,):
        for inst in self.room.copy():
            self._add_to_bar(inst)

    def _set_grap_mode(self, on:bool):
        self.grasped = on
        self.volume_bar.show = on
        self.x.show = not on
        if on:
            self.reset_btn.show = False


    def release(self, azimuth:float=None, elevation:float=None,)->bool:
        if self.selected is None or self.grasped == False:
            return False
        
        if valide_angle_area(self.selected.center, self.frame.shape):
            self.selected_size_change(-self.sel_size)
            self._add_to_room(self.selected)
            self.selected_set_angle(azimuth=azimuth, elevation=elevation)
        else:
            self._add_to_bar(self.selected)
            self.selected_set_angle(azimuth=None, elevation=None)

        self.info_dict = self.selected.get_info()
        self._set_grap_mode(False)
        if self.room or [inst for inst in self.bar if inst.volume != S.instrument_start_volume]:
            self.reset_btn.show = True
        else:
            self.reset_btn.show = False
        return True

    def move(self, pos:tuple[int,int])-> bool:
        if not self.grasped:
            return False
        
        self.selected.set_center(pos)
        return True

    def selected_set_angle(self, azimuth:float, elevation:float):
        self.selected.azimuth = azimuth
        self.selected.elevation = elevation

    def get_info(self):
        if self.info_dict:
            r = self.info_dict.copy()
            self.info_dict.clear()
            return r
        return None


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