from Vision_Robotic_Arm_Gesture_Recognition.analyse import SaveFrameStatus, CaptureStatus
# c = CaptureStatus(None)
# s = SaveFrameStatus(None)
# name = r"C:\Users\Ampelman\Desktop\Masterarbeit\open close status data for videos\WIN_20260609_19_51_56_Pro.mp4frame_and_open_close_manual_status"
# end = '.txt'
# s.load_from_file(name+end)
# c.saved = s.get_status_for_each_frame()
# c.save_to_file(name+"_each_frame"+end)
from collections import Counter
results = Counter({4:0})
for key in ['fgf', '343', '3', 3, 4,'3','tztz','fgf','fgf',3]:
    results[key] += 1

print(results)
print({1:1})

# import ast
# import json
# names = [
# r"C:\Users\Ampelman\Desktop\Masterarbeit\open close status data for videos\WIN_20260609_19_51_56_Pro.mp4frame_and_open_close_manual_status",
# r"C:\Users\Ampelman\Desktop\Masterarbeit\open close status data for videos\WIN_20260622_14_46_06_Pro.mp4frame_and_open_close_manual_status",
# r"C:\Users\Ampelman\Desktop\Masterarbeit\open close status data for videos\WIN_20260622_14_50_01_Pro.mp4frame_and_open_close_manual_status",
# r"C:\Users\Ampelman\Desktop\Masterarbeit\open close status data for videos\WIN_20260622_15_27_19_Pro.mp4frame_and_open_close_manual_status"
# ]



# def f(name):
#     data = []

#     with open(name+'.txt', "r", encoding="utf-8") as f:
#         for line in f:
#             line = line.strip()

#             if not line:
#                 continue

#             data.append(ast.literal_eval(line))

#     with open(name+'.json', "w", encoding="utf-8") as f:
#         json.dump(data, f, indent=4)

#     print(f"{len(data)} Einträge nach {name+'.json'} gespeichert.")


# for name in names:
#     f(name)