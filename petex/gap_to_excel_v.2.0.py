# скрипт для извлечения данных из Prosper через OpenServer

import win32com.client
import sys
import os
import time
import tqdm
import pandas as pd

start_time = time.time()

class OpenServer():
    # "Class for holding ActiveX reference. Allows license disconnection"
    def __init__(self):
        self.status = "Disconnected"
        self.OSReference = None
    
    def Connect(self):
        self.OSReference = win32com.client.Dispatch("PX32.OpenServer.1")
        self.status = "Connected"
        print("OpenServer connected")
        
    def Disconnect(self):
        self.OSReference = None
        self.status = "Disconnected"
        print("OpenServer disconnected")

def GetAppName(sv):
    # function for returning app name from tag string
    pos = sv.find(".")
    if pos < 2:
        sys.exit("GetAppName: Badly formed tag string")
    app_name = sv[:pos]
    if app_name.lower() not in ["prosper", "mbal", "gap", "pvt", "resolve", "reveal"]:
        sys.exit("GetAppName: Unrecognised application name in tag string")
    return app_name

def DoCmd(OpenServe, cmd):
    # perform a command and check for errors
    lerr = OpenServe.OSReference.DoCommand(cmd)
    if lerr > 0:
        err = OpenServe.OSReference.GetErrorDescription(lerr)
        OpenServe.Disconnect()
        sys.exit("DoCmd: " + err)

def DoSet(OpenServe, sv, val):
    # set a value and check for errors
    lerr = OpenServe.OSReference.SetValue(sv, val)
    app_name = GetAppName(sv)
    lerr = OpenServe.OSReference.GetLastError(app_name)
    if lerr > 0:
        err = OpenServe.OSReference.GetErrorDescription(lerr)
        OpenServe.Disconnect()
        sys.exit("DoSet: " + err)

def DoGet(OpenServe, gv):
    # get a value and check for errors
    get_value = OpenServe.OSReference.GetValue(gv)
    app_name = GetAppName(gv)
    lerr = OpenServe.OSReference.GetLastError(app_name)
    if lerr > 0:
        err = OpenServe.OSReference.GetErrorDescription(lerr)
        #OpenServe.Disconnect()
        #sys.exit("DoGet: " + err)
        #print("DoGet: " + err)
        # if error rerurn 0
        return None
    return get_value

def DoSlowCmd(OpenServe, cmd):
    # perform a command then wait for command to exit and check for errors
    step = 0.001
    app_name = GetAppName(cmd)
    lerr = OpenServe.OSReference.DoCommandAsync(cmd)
    if lerr > 0:
        err = OpenServe.OSReference.GetErrorDescription(lerr)
        OpenServe.Disconnect()
        sys.exit("DoSlowCmd: " + err)
    while OpenServe.OSReference.IsBusy(app_name) > 0:
        if step < 2:
            step = step*2
        time.sleep(step)
    lerr = OpenServe.OSReference.GetLastError(app_name)
    if lerr > 0:
        err = OpenServe.OSReference.GetErrorDescription(lerr)
        OpenServe.Disconnect()
        sys.exit("DoSlowCmd: " + err)

def DoGAPFunc(OpenServe, gv):
    DoSlowCmd(gv)
    DoGAPFunc = DoGet(OpenServe, "GAP.LASTCMDRET")
    lerr = OpenServe.OSReference.GetLastError("GAP")
    if lerr > 0:
        err = OpenServe.OSReference.GetErrorDescription(lerr)
        OpenServe.Disconnect()
        sys.exit("DoGAPFunc: " + err)
    return DoGAPFunc

def OSOpenFile(OpenServe, theModel, appname):
    DoSlowCmd(OpenServe, appname + '.OPENFILE ("' + theModel + '")')
    lerr = OpenServe.OSReference.GetLastError(appname)
    if lerr > 0:
        err = OpenServe.OSReference.GetErrorDescription(lerr)
        OpenServe.Disconnect()
        sys.exit("OSOpenFile: " + err)

def OSSaveFile(OpenServe, theModel, appname):
    DoSlowCmd(OpenServe, appname + '.SAVEFILE ("' + theModel + '")')
    lerr = OpenServe.OSReference.GetLastError(appname)
    if lerr > 0:
        err = OpenServe.OSReference.GetErrorDescription(lerr)
        OpenServe.Disconnect()
        sys.exit("OSSaveFile: " + err)


# get data list
def get_date_list(n_dates):
    date_list = []
    for i in range(n_dates):
        date_list.append(DoGet(petex, f"GAP.MOD[i].EQUIP[j].PREDRES.DATES[{i}].DATESTR")[:-1])
    #print(date_list)
    return date_list
        
    
# get equipment list
def get_equip_list(equip_type):
    if equip_type == 'WELL':
        equip = DoGet(petex, f"GAP.MOD[0].{equip_type}[$].Label").split('|')
        
    elif equip_type == 'PIPE':
        equip = DoGet(petex, f"GAP.MOD[0].PIPE[$].Label").split('|')

    else:
        equip = DoGet(petex, f"GAP.MOD[0].{equip_type}[$].Label").split('|')

    equip = [elem for elem in equip if elem != '']

    return sorted(equip)


# get parameters of equipment as DataFrame
def get_param(equip_list, equip_type, param_name):
    '''
    GAP param_name:
    буферное: GAP.MOD[{PROD}].WELL[{8504}].PREDRES[{01.02.2021}].FWHP
    drawdown: GAP.MOD[{PROD}].WELL[{8504}].PREDRES[{01.01.2021}].DrawDown
    Qн        GAP.MOD[{PROD}].WELL[{8504}].PREDRES[{01.01.2021}].OILRATE
    температ буф GAP.MOD[{PROD}].WELL[{8503}].PREDRES[{01.01.2021}].FWHT
    лин давл: GAP.MOD[{PROD}].JOINT[{J Choke 8503}].PREDRES[{01.01.2021}].PRES
    '''
    df = pd.DataFrame({'Date': date_list})
    #print('\n длина списка дат: ', len(date_list))
    for equip in equip_list:
        
        param_list = []
        try:
            # если для элемента оборудования есть массив данных, то получаем его
            if equip_type != 'PIPE':
                param = DoGet(petex, 'GAP.MOD[{PROD}].' + f'{equip_type}' + '[{' +
                            str(equip) + '}].PREDRES[' + '$].' + f'{param_name}')

            elif equip_type == 'PIPE':
                # GAP.MOD[{PROD}].PIPE[{12}].PREDRES[{01.01.2025}].AVGLIQRATE
                #print('GAP.MOD[{PROD}].' + f'{equip_type}' + '[{' +
                #            str(equip) + '}].PREDRES[' + '$].' + f'{param_name}')
                
                param = DoGet(petex, 'GAP.MOD[{PROD}].' + f'{equip_type}' + '[{' +
                            str(equip) + '}].PREDRES[' + '$].' + f'{param_name}')
                
                #GAP.MOD[{PROD}].PIPE[112].Desc[1].Type
                #GAP.MOD[{PROD}].PIPE[108].Desc[1].Length
##                param = DoGet(petex, 'GAP.MOD[{PROD}].PIPE' + '[{' +
##                            str(equip) + '}].Desc[1].' + f'{param_name}')
##                print('GAP.MOD[{PROD}].PIPE' + '[{' + str(equip) + '}].Desc[1].' + f'{param_name}')

            else:
                print('Другое оборудование')

            param_list = param.split('|')
            #print('\n param list =', type(param_list), param_list)

            # убираем значения 3.4e+35, которые прилетают из GAP вместо None
            param_list_1 = [None if x == '3.4e+35' else x for x in param_list]

            # конвертируем строковые элементы в числа
            param_list_2 = []
            for param in param_list_1:
                try:
                    param_list_2.append(float(param))
                except:
                    param_list_2.append(param)


            df[f'{equip}'] = pd.Series(param_list_2)

            #print('df', df)
            print(f'Для оборудования {equip} добавлен {param_name} ')

        # если для оборудования нет прогноза, пропускаем
        except:
            print(f'Нет параметра {param_name} для оборудования {equip}  ')
            continue
    return df, param_name



# Script wrapped in a try statement to ensure license is disconnected in case of error
try:
    # Initialises an 'OpenServer' class
    petex = OpenServer()
    
    # Creates ActiveX reference and holds a license
    petex.Connect()
    
    # Perform functions
    cwd = os.getcwd() # current working directory


## ====================  СЕКЦИЯ ПАРАМЕТРОВ НАСТРОЙКИ СКРИПТА ======================
    # РАБОТАЕМ С ОТКРЫТЫМ В ДАННЫЙ МОМЕНТ ФАЙЛОМ
    # Имя файла с которым работаем
##    file_name = '\PROSPER\9205 choke sep 2020.12.09 73tubing.Out'
##    OSOpenFile(petex, cwd + file_name, 'PROSPER')
    #print('Открываем файл . . .')
    #OSOpenFile(petex, r'D:\work\2020.12_models\PES_ACH2\PES_ACH.gap', 'gap')
    # OSOpenFile(petex, r'D:\work\2020.12_models\En_Yaha\ENYAHA_AFTER_EXPERT Jun 2020\PES_YAHA.gap', 'gap')
    #print('Файл открыт')

    # задаём имя выходного файла
    output_file = 'output_from_gap.xlsx'
    
    # задаём тип оборудование для извлечения
    '''
    типы оборудований: 'WELL', 'PIPE', 'JOINT', 
                       INLCHK, EQUIP, VALVE, TANK, PUMP, SEP, SINK, COMP, SOURCE...
    '''

    equip_type = 'WELL'
    #equip_type_list = ['WELL', 'JOINT', 'PIPE']

    # задаём список параметров для извлечения
    # для скважин: OPFREQ - частота ЭЦН
    #param_list = ['FWHP','MANPRES']
    # FWHP - Pбуф,
    param_list_well = ['OILRATE', 'GASRATE','WATRATE','LIQRATE','MANPRES','FWHP','FBHP','DrawDown','WCT', \
                        'MixtureVelocity','ErosionalVelocity','AVGGASRATE'] # 'OPFREQ'
    # для Joint
    param_list_joint = ['OILRATE','GASRATE','WATRATE','LIQRATE','PRES','WCT']
    # для SINK (УКПГ/УПН)
    param_list_sink = ['OILRATE', 'GASRATE', 'WATRATE', 'LIQRATE', 'PRES', 'NUMACTIVEWELLS']
    # для PIPE
    param_list_pipe = ['OILRATE','GASRATE','WATRATE','LIQRATE','WCT','PRESSUREDROP','PRESIN','PRESOUT', \
                  'VELOCITY','MAXPRES','CHOKESIZE']
    # Конструкции сети: PIPE => input => Description: GAP.MOD[{PROD}].PIPE[112].Desc[1].Type
    param_list_pipe_descrip = ['Type', 'Length', 'TVD', 'ID', 'Roughness', 'HTC']

## ====================  КОНЕЦ СЕКЦИИ ПАРАМЕТРОВ НАСТРОЙКИ СКРИПТА ======================
    

    # извлекаем количество дат в прогнозе
    n_dates = int((DoGet(petex, "GAP.MOD[i].EQUIP[j].PREDRES.DATES.COUNT")[:-1]))
    
    # извлекаем список дат прогноза
    date_list = get_date_list(n_dates)

    # извлекаем список оборудования указанного выше типа
    #for equip_type in equip_type_list:
    equip_list = get_equip_list(equip_type)
    #equip_list = ['7301', '7306_2']
    print('Извлекаем параметры для списка оборудования: ', equip_list)

    # тест
    #print(DoGet(petex, 'GAP.MOD[{PROD}].WELL[{7003}].PREDRES[0].OILRATE'))

    # извлекаем данные и сохраняем в файл
    try:
        with pd.ExcelWriter(output_file) as writer:
            #for param in tqdm(param_list):
            if equip_type == 'WELL':
                for param in param_list_well:
                    df, param_name = get_param(equip_list, equip_type, param)
                    df.to_excel(writer, sheet_name=f'{equip_type}_{param_name}', index=False, freeze_panes=(1,1))
                
            elif equip_type == 'JOINT':
                for param in param_list_joint:
                    df, param_name = get_param(equip_list, equip_type, param)
                    df.to_excel(writer, sheet_name=f'{equip_type}_{param_name}', index=False, freeze_panes=(1,1))
                
            elif equip_type == 'PIPE':
                for param in param_list_pipe:
                    df, param_name = get_param(equip_list, equip_type, param)
                    df.to_excel(writer, sheet_name=f'{equip_type}_{param_name}', index=False, freeze_panes=(1,1))
                    
            elif equip_type == 'SINK':
                for param in param_list_pipe_sink:
                    df, param_name = get_param(equip_list, equip_type, param)
                    df.to_excel(writer, sheet_name=f'{equip_type}_{param_name}', index=False, freeze_panes=(1,1))

            else:
                print('Неизвестное оборудование!')
                    
        print(f'Данные сохранены в файл {output_file}')
        print(f'--- Время выполнения: {round((time.time() - start_time), 0)} секунд ---')
                
    except Exception:
        print('                ==============================\n  \
               ########    ОШИБКА   #########\n \
                    Данные не сохранены!!!\n \
                        Файл открыт? \n \
               ===============================')

finally:
    # Required to close the license otherwise remains checked out
    petex.Disconnect()
