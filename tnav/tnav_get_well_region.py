import pandas as pd

region_name = 'FIPWELLS'  # <== задаём имя целевого региона

# извлекаем список всех скважин и формируем словарь
well_list = []
for well in get_all_wells():
	well_list.append(str(well.name))
well_reg_dict = { well : int(0) for well in well_list }

i = 1
# итерируемся по скважинам
for well in get_all_wells():
	# извлекаем спиок все connection для каждой скважины
	perforations = well.get_connections_from_branch(branch_id=0)
	# итерируемся по каждомуу connection
	for perforation in perforations:
		# извлекаем номер региона итерируемого connection
		current_reg_num = get_fip_region(region_name, i + 1 ).number
		# проверяем есть ли в словаре записанный номер региона для скважины
		if well_reg_dict[well.name] == 0:
			# если нет, прописываем текущий
			well_reg_dict[well.name] = current_reg_num
		# если номер региона прописан, проверяем что он не отличается от нового региона
		elif well_reg_dict[well.name] != 0 and well_reg_dict[well.name] != current_reg_num:
			# в этом случае пишем об ошибке
			print('Внимание!!! Скважина:', well.name, 'расположена в разных регионах:', well_reg_dict[well.name], current_reg_num)	
	i += 1
	
df = pd.DataFrame(well_reg_dict.items(), columns=['well', 'region']).sort_values(by=['well'])
print(df.to_string(index=False))