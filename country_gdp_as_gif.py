#!/usr/bin/env python3

################################################################################
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -#
#	                 Script developed by Alex Borges, dev.amborges@gmail.com.  #
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -#
#     PROJECT: Python3_ChatGPT3_GDP_GIF                                        #
#																			   #
#     Summary: This script generates a GIF of a borderline country followed by #
# its regions / state capitals. These capitals have a red ball that will       #
# represent the amount of GDP value (in million USD) acquired by this region / #
# state over some years. The user must inform the country's full name, and the #
# first year of GDP value can be changed, as the last year, but cannot trespass#
# 2020. This script will obtain from ChatGPT-3 the regions / state names and   #
# their respective GDP values over the years. Also, we request from ChatGPT-3  #
# the coordination of the country and their capitals. All captured data is     #
# stored in a specific folder, and a final gif is created. Except in case of   #
# any failure.                                                                 #
#																			   #
#																			   #
#											      Version 1.0. March, 16, 2021 #
################################################################################


#The main objective of this scrit is create a table contain the states of 'COUNTRY' 
# with their respective GDP values along the years inside the intervall informed


#importing packages
import openai
import os
import random as rnd
import pandas as pd
import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.geometry import Point
from PIL import Image

#loading OpenAI API personal key
openai.api_key = os.environ["OPENAI_API_KEY"]


#We configure variables here. But also it is possible to change to sys.argv, if required

#Configuring main variables
#Name of country
COUNTRY        = 'Spain'

#Year of starting capture GDP values
FIRST_YEAR     = 2010

#Year of last GDP values. ChatGPT-3 did not know anything after september, 2021. 
# So, we must not transpass 2020 for safety
LAST_YEAR      = 2020 

#Markersize to be applied to the figures. I think 10k is a good number.
MAX_MARKERSIZE = 10000



#############################
#####                   #####
#####     FUNCTIONS     #####
#####                   #####
#############################

#The following function receive a year and return a list of the pair State:GDP. 
# This function also reformatting this string in a list of three values: state-GDP
def getting_GDP(year):
	#connect and makes the question
	completion = openai.ChatCompletion.create(
		model="gpt-3.5-turbo",
		messages=[{"role": "user",
		           "content": "return a list and no other comment, considering the states of {},\
				     which are sorted by alphabetical order, inform the GDP of these states in {}, \
					 in that followed format: state_name:value_in_million_usd".format(COUNTRY, year)
		         }]
	)
	
	EMPTY = [[None, None], False]
	
	#converting the json answer in a string
	ans = completion.choices[0].message.content.strip()
	
	#avoiding failed answers
	if ("unfortunately" in ans.lower() ) or ("sorry" in ans.lower() ):
		print("::FAILED::{}".format(ans))
		return EMPTY
	else:
		try:
			#eventually returns value in billions instead of millions ¬.¬
			ans = ans.replace("million", "").replace("$", "").replace("USD", "")
			billion_allert = False
			if("billion" in ans):
				ans = ans.replace("billion", "")
				billion_allert = True
			
			#capturing all values and store them as float
			ans = ans.replace(",", "").split("\n")
			_ans = []
			for element in ans:
				state, gdp = element.split(":")
				_ans.append([state, float(gdp) * (1000 if billion_allert else 1)])
			return [_ans, True]
		except Exception as excpt:
			print("::!ERROR: {}::!".format(excpt), end="")
			print("::!MSG RECEIVED: {}::!".format(ans), end="")
			return EMPTY


#this function capture the country coordinates and returns a list
def getting_country_coordinates():
	completion = openai.ChatCompletion.create(
		model="gpt-3.5-turbo",
		messages=[{"role": "user",
		           "content": "return a list and no other comment, informing the coordinates \
					of the country {}. In that followed format: \
						min_longitude:min_latitude:max_longitude:max_latitude".format(COUNTRY)
		         }]
		)
	#converting the json answer in a string
	ans = completion.choices[0].message.content.strip()
	
	ans = ans.split(":")
	
	#return with one extra point as margin:
	return float(ans[0]) - 1., float(ans[1]) - 1., float(ans[2]) + 1., float(ans[3]) + 1.


#this function capture the country name and returns a list of coordinates of all State capitals 
# of this country in a DataFrame format
def getting_capital_coordinates():
	completion = openai.ChatCompletion.create(
		model="gpt-3.5-turbo",
		messages=[{"role": "user",
		           "content": "return a list and no other comment, considering the States of {}, \
					which are sorted by alphabetical order, the longitudes and latitudes of their \
					capitals. In that followed format: state_name:capital_name:longitude:latitude".format(COUNTRY)
		         }]
		)
	#converting the json answer in a string
	ans = completion.choices[0].message.content.strip()
	
	data = []
	for row_element in ans.split("\n"):
		if(len(row_element) > 2):
			state, capital, longitude, latitude = row_element.split(":")
			data.append([state, capital, float(longitude), float(latitude)])
	
	df = pd.DataFrame(data, columns=["state", "capital", "longitude", "latitude"])
	
	#creating a Point for the capital coordinate
	df["coordinate"] = df.apply(lambda x: Point(x['longitude'], x['latitude']), axis=1)
	
	return df
	
#function that receive a dataframe followed by a year, making a png map
def dataframe_to_png(df, year, max_gdp, min_lo, min_la, max_lo, max_la, where_to_save):
	#loading the world map
	world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
	
	#creating a proportional marker size according to greatest GDP value founded
	df["prop_gpd"] = MAX_MARKERSIZE * (df["gdp_{}".format(year)] / max_gdp)
	
	#converting dataframe into geodataframe
	gdf = gpd.GeoDataFrame(df, geometry=df.coordinate)
	
	#plot map, but only with country limits
	ax = world.boundary.plot(figsize=(10, 10))

	#plot capitals
	gdf.plot(marker='o', color='red', markersize="prop_gpd", ax=ax)

	#plot capitals name
	for idx,row in df.iterrows():
		#column - value
		# 1 - capital name
		# 2 - longitude
		# 3 - latitude
		pos_x = row[2] + .05
		pos_y = row[3]
		text_to_plot = "{}".format(row[1])
		ax.text(pos_x, pos_y,text_to_plot, horizontalalignment='left')
	
	#I apply a zoom on country
	ax.set_xlim(min_lo, max_lo)
	ax.set_ylim(min_la, max_la)
	
	#adding title to the graph
	plt.title("GDP for the year {} of all states in {}, represented by state capitals".format(year, COUNTRY))


	#saving the plot
	file_name = "{}/gdp_{}.png".format(where_to_save, year)
	plt.savefig(file_name)
	return file_name
		


############################
#####                   ####
#####    __MAIN()__     ####
#####                   ####
############################

print("Start of script execution:")
print("Connect with ChatGPT-3 to obtain the GDP values of all state in {}".format(COUNTRY))

#1st, create a folder with the name of country
COUNTRY_PATH = "{}_{}".format(COUNTRY, rnd.randint(1,9999))
while(os.path.exists(COUNTRY_PATH)):
	#This loop allow the user to repeat this script without troubles
	COUNTRY_PATH = "{}_{}".format(COUNTRY, rnd.randint(1,9999))
os.mkdir(COUNTRY_PATH)
print("Dear user, all data generated by this scrit will be saved on {} directory.".format(COUNTRY_PATH))

#2st, capture the country coordinates, it will be used to zoom map on the country
min_longitude, min_latitude, max_longitude, max_latitude = getting_country_coordinates()

#BACKUP
f = open("{}/country_coordinates.txt".format(COUNTRY_PATH), "w")
f.write("min_longitude: {}\nmin_latitude: {}\nmax_longitude: {}\nmax_latitude: {}".format(min_longitude, 
											                                              min_latitude, 
																						  max_longitude, 
																						  max_latitude))
f.close()

#3nd, capture the country states capital and their coordinates
df_cities_coordinate = getting_capital_coordinates()

#BACKUP
df_cities_coordinate.to_csv("{}/df_cities_coordinate.csv".format(COUNTRY_PATH), index=False)

max_GDP = -1. #this variable is used as divisor
years_that_exists = [] #this variable store all years that was possible to obtain something

#LOOP year-by-year, I'm adding +1 to capture 2020.
for year in range(FIRST_YEAR, LAST_YEAR + 1):
	print("Wait, working on year {}...".format(year), end="")
	#4th, capture de GPD values of the year
	gdp, success = getting_GDP(year)
	if not success:
		#if for some reason the ChatGPT-3 don't return a valid value, ignore this year
		print("[[FAIL]]")
		continue
	
	years_that_exists.append(year)

	#5th, convert list into dataframe
	df_gdp = pd.DataFrame(gdp, columns=["state", "gdp_{}".format(year)])
	
	#6th, capturing the greatest GDP of all data
	_gdp_max = max(df_gdp["gdp_" + str(year)])
	if(_gdp_max > max_GDP):
		max_GDP = _gdp_max

	#7th, merging dataframes into one
	df_cities_coordinate = pd.merge(df_cities_coordinate, df_gdp, on="state")

	print("[[SUCCESS]]")

#BACKUP
df_cities_coordinate.to_csv("{}/df_cities_coordinate.csv".format(COUNTRY_PATH), index=False)
f = open("{}/max_GDP.txt".format(COUNTRY_PATH), "w")
f.write("max_GDP: {}".format(max_GDP))
f.close()

#8th, export actual data into figures
png_files = []
for year in years_that_exists:
	fname = dataframe_to_png(df_cities_coordinate,
		                     year, 
		                     max_GDP,
		                     min_longitude,
		                     min_latitude,
		                     max_longitude,
		                     max_latitude,
					         COUNTRY_PATH
		                    )
	png_files.append(fname)

#9th, convert saved figures in an animated GIF
frames = []
for filename in png_files:
    frames.append(Image.open(filename))
frames[0].save("animated_{}.gif".format(COUNTRY), 
	           format='GIF', 
			   append_images=frames[1:], 
			   save_all=True, 
			   duration=100, 
			   loop=0
			  )

print("End of script execution. Thanks for using.")
