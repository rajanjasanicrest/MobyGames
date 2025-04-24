import pandas as pd
import json

unwanted = ["TRS-80 Model 100", "Triton", "IBM 5100", "HP Programmable Calculator", "HP Series 80", "HP 9800", "Heathkit H11", "GVM", "Compucorp Programmable Calculator", "Compal 80", "Casio Programmable Calculator", "Bubble", "Auto Response Board", "Astral 2000", "Altair 680", "Altair 8800", "Modular Game System", "Blu-ray Disc Player", "Interton Video 2000", "iiRcade", "Jolt", "KIM-1", "OOParts", "Photo CD", "Poly-88", "SK-VM", "Sol-20", "SRI-500/1000", "SWTPC 6800", "Taito X-55", "Tektronix 4050", "TI Programmable Calculator", "Versatile", "Wang 2200", "Xerox Alto", "N-Gage (service)", "Ouya", "Zeebo", "Antstream", "iiRcade", "Magic Leap", "Oculus Go", "Palm OS", "Quest", "HD DVD Player", "HP Oscilloscope", "J2ME", "Mainframe", "Sharp Zaurus", "Pebble", "Roku", "AirConsole", "bada", "BeOS", "Blacknut", "BREW", "Danger OS", "DoJa", "ExEn", "Feature phone", "Fire OS", "Freebox", "G-cluster", "GameStick", "GIMINI", "Gloud", "Glulx", "GNEX", "Intel 8008", "Intel 8080", "Intel 8086 / 8088", "KaiOS", "Luna", "Maemo", "MeeGo", "Mophun", "MOS Technology 6502", "Motorola 6800", "Motorola 68k", "Newton", "OnLive", "PlayStation Now", "Plex Arcade", "SC/MP", "Signetics 2650", "Stadia", "Symbian", "TADS", "Terminal", "Tizen", "tvOS", "visionOS", "watchOS", "webOS", "Windows Apps", "Windows Mobile", "Windows Phone", "WIPI", "Xbox Cloud Gaming", "Z-machine", "Zilog Z80", "Zilog Z8000", "Zune"]

# Example list of JSON objects
with open('mobygames_platforms.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

for console in data:
    if console['platform'] in unwanted:
        data.remove(console)


with open('mobygames_platforms.json', 'w', encoding='utf-8') as file:
    json.dump(data, file, indent=4)



# # Convert the list of dictionaries to a DataFrame
# df = pd.DataFrame(data)

# # Write to Excel
# output_file = "platforms.xlsx"
# df.to_excel(output_file, index=False)

# print(f"Excel file '{output_file}' has been created.")