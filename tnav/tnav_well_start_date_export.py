# Скрипт для извлечения дат запуска скважин из расчёта tNavigator
# скрипт запускается из графического интерфейса tNav

# извлекаем имя текущей модели
models = get_all_models()
print(models[0])

# извлекаем список всех скважин
well_list = []
for well in get_all_wells():
    #print(well.name)
    well_list.append(str(well.name))
print('Список скважин:', well_list)

# формируем словарь
well_status_dict = { well : int(0) for well in well_list }

# извлекаем список дат
dates = get_all_timesteps()

# итерируемся по списку скважин
well_status_list = []
for well in well_list:
    # извлекаем статус скважины для текущей модели и приводи его к списку
    well_status_list = wstat[get_well_by_name(well)].fix(model=models[0]).to_list ()

    # находим индекс  когда статус кважины = 1 (добывающая)
    try:
        well_start = well_status_list.index(1)
        # обновляем словарь датой смены статуса
        well_status_dict[well] = dates[well_start - 1].name
    except:
        pass

print(well_status_dict)
