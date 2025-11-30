def calculate_fat(user, weight, imp50):
    age = user['age']
    height = user['height']
    is_male = user['is_male']
    activity_level = user['activity_level']

    activity_corr_fac = 0.0
    if activity_level == 4:
        activity_corr_fac = 2.5 if is_male else 2.3
    elif activity_level == 5:
        activity_corr_fac = 4.3 if is_male else 4.1

    sex_corr_fac = 0.250 if is_male else 0.214
    activity_sex_div = 65.5 if is_male else 55.1

    return (1.847 * weight * 10000.0 / (height * height) + 
            sex_corr_fac * age + 0.062 * imp50 - 
            (activity_sex_div - activity_corr_fac))

def calculate_water(user, weight, imp50):
    age = user['age']
    height = user['height']
    is_male = user['is_male']
    activity_level = user['activity_level']

    activity_corr_fac = 0.0
    if 1 <= activity_level <= 3:
        activity_corr_fac = 2.83 if is_male else 0.0
    elif activity_level == 4:
        activity_corr_fac = 3.93 if is_male else 0.4
    elif activity_level == 5:
        activity_corr_fac = 5.33 if is_male else 1.4

    return ((0.3674 * height * height / imp50 + 
            0.17530 * weight - 0.11 * age + 
            (6.53 + activity_corr_fac)) / weight * 100.0)

def calculate_muscle(user, weight, imp50, imp5):
    age = user['age']
    height = user['height']
    is_male = user['is_male']
    activity_level = user['activity_level']

    activity_corr_fac = 0.0
    if 1 <= activity_level <= 3:
        activity_corr_fac = 3.6224 if is_male else 0.0
    elif activity_level == 4:
        activity_corr_fac = 4.3904 if is_male else 0.0
    elif activity_level == 5:
        activity_corr_fac = 5.4144 if is_male else 1.664

    return (((0.47027 / imp50 - 0.24196 / imp5) * height * height + 
            0.13796 * weight - 0.1152 * age + 
            (5.12 + activity_corr_fac)) / weight * 100.0)    
