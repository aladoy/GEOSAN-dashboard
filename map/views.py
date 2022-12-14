from django.shortcuts import render
import folium
from branca.colormap import linear
from branca.colormap import LinearColormap
import pandas as pd
from .models import Communes
import geopandas as gpd
from . import forms
from folium import plugins
import os
import plotly.express as px
import plotly.graph_objects as go
from plotly.graph_objs import *
import numpy as np
from folium.plugins import FloatImage, MarkerCluster, FeatureGroupSubGroup
from map.utils import *
from map.utils_var import *

# Create your views here.

def index(request):

    m = folium.Map(location = [46.61280022381356, 6.61517533257687],
        tiles=None,
        min_lat=46.2,max_lat=47.3,min_lon=5.9,max_lon=7.2, 
        zoom_start=10, max_zoom=15, min_zoom=9,
        zoom_control=False,
        )
    folium.TileLayer('cartodbpositron', control=False).add_to(m)
    
    chart= ""
    hist=""
    legend_color_scale=""
    legend_text=""
    commune_request_name=""
    current_commune_text=""
    var_name=""
    limitations_informations=""
    unit = ""
    legend_moyenne_text = ""

    communes_data = './geojson/Caracterisation_PCA_wgs_84_2.csv'

    communes_data = pd.read_csv(communes_data)
    communes_names = communes_data['Nom_CMN']
    communes_names = sorted(communes_names)

    highlight_function = lambda x: {
    'color': 'red', # stroke becomes red
    'opacity' : 0.9,
    'weight': 4,
    'dashArray' : '3, 6' # transforms the solid stroke to a dashed stroke
    }

    geojson_dir = geojson_dir = os.path.join(os.getcwd(),'geojson')

    add_base_layers(m,highlight_function, geojson_dir)
    add_base_places(m,geojson_dir)
    #add_categorical_legend(m)

    # select data type to display:
    list_env = ["PM10","NOISE"]
    list_demo = ["b21btot","RPNF"]
    list_accessibility = ["D_PHARMA","MEDINCM"]

    if request.method=="POST":

        commune_request_name = request.POST["commune_name"]
        var_name = request.POST["var_name"]

        gdf = gpd.read_file("./geojson/var_hectares_wgs.geojson")

        map_dict = gdf.set_index('reli')[var_name].to_dict()

        gdf_kept = gdf[gdf['name']==commune_request_name]

        mean_commune = gdf_kept[var_name].mean()

        gdf_to_dissolve = gdf_kept[['name','geometry']]
        gdf_to_dissolve = gdf_to_dissolve.to_crs('2056')
        gdf_to_dissolve = gdf_to_dissolve.dissolve(by='name').centroid

        m.location = [gdf_to_dissolve[0].y, gdf_to_dissolve[0].x]

        hec_group = folium.FeatureGroup(name=var_name)
        
        if var_name in list_env:

            [x_list, x_text, href, limitations_informations, unit] = select_var_limites(var_name, gdf)
            
            x_vect = [x_list[0]+(x_list[1]-x_list[0])/2, 
                        x_list[1]+(x_list[2]-x_list[1])/2, 
                        x_list[2]+(x_list[3]-x_list[2])/2, 
                        x_list[3]+(x_list[4]-x_list[3])/2, 
                        x_list[4]+(x_list[5]-x_list[4])/2]

            width_vect = [x_list[1]-x_list[0], x_list[2]-x_list[1], x_list[3]-x_list[2], x_list[4]-x_list[3], x_list[5]-x_list[4]]
            color_vect = []

            for elem in x_vect:
                color_vect.append(get_color_discrete_value(elem, x_list[1], x_list[2], x_list[3], x_list[4]))

            data_tuples = list(zip(x_vect,width_vect,color_vect))
            df_test = pd.DataFrame(data_tuples, columns=['x','width','color'])

            [legend_color_scale, legend_text, hist, chart, legend_moyenne_text] = add_informations(df_test, x_list, mean_commune, gdf_kept,var_name,map_dict, x_text, href, unit, commune_request_name)

            folium.GeoJson(gdf_kept, 
                name='geojson',
                zoom_on_click=False,
                tooltip=folium.GeoJsonTooltip(fields=['name', var_name]),
                style_function= lambda feature:{
                'fillColor': get_color_discrete(feature,var_name,x_list[1], x_list[2], x_list[3], x_list[4]),
                'fillOpacity': 1,
                'weight':0.1,
                },
                highlight_function=highlight_function).add_to(hec_group)

            m.fit_bounds(hec_group.get_bounds())

            gdf_communes = gpd.read_file('./shapefiles/Caracterisation_PCA.shp')
            commune_a_intersecter_geom = gdf_communes[gdf_communes['Nom_CMN']==commune_request_name].geometry.buffer(1000)
            gdf_communes_geom = gdf_communes.geometry

            result_touches = gdf_communes_geom.intersects(commune_a_intersecter_geom.iloc[0])
            
            communes_kept_indexes = []
            for index, elem in enumerate(result_touches):
                if elem == True:
                    name_of_commune = gdf_communes.iloc[index].Nom_CMN
                    communes_kept_indexes.append(index)
                    if name_of_commune != commune_request_name:
                        folium.GeoJson(gdf[gdf['name']==name_of_commune], 
                            name='geojson',
                            zoom_on_click=False,
                            tooltip=folium.GeoJsonTooltip(fields=['name', var_name]),
                            style_function= lambda feature:{
                            'fillColor': get_color_discrete(feature,var_name,x_list[1], x_list[2], x_list[3], x_list[4]),
                            'fillOpacity': 1,
                            'weight':0.1,
                            },
                            highlight_function=highlight_function).add_to(hec_group)

            hec_group.add_to(m)
            m.keep_in_front(hec_group)

        '''elif var_name in list_accessibility:
            
            gdf_communes = gpd.read_file('./shapefiles/Communes_WGS.shp')
            gdf_communes = gdf_communes.to_crs('2056')
            commune_a_intersecter_geom = gdf_communes[gdf_communes['Nom_CMN']==commune_request_name].geometry.buffer(1000)
            gdf_communes_geom = gdf_communes.geometry

            result_touches = gdf_communes_geom.intersects(commune_a_intersecter_geom.iloc[0])
            
            communes_kept_indexes = []
            communes_kept_names = []
            for index, elem in enumerate(result_touches):
                if elem == True:
                    name_of_commune = gdf_communes.iloc[index].Nom_CMN
                    communes_kept_indexes.append(index)
                    communes_kept_names.append(name_of_commune)

            gdf_kept_buffer = gdf[gdf['name'].isin(communes_kept_names)]
            var_values = gdf_kept_buffer[var_name]
            max_communes = np.nanmax(var_values)
            min_communes = np.nanmin(var_values)

            range_values = max_communes-min_communes

            folium.GeoJson(gdf_kept, 
                name='geojson',
                zoom_on_click=True,
                tooltip=folium.GeoJsonTooltip(fields=['name', var_name]),
                style_function= lambda feature:{
                'fillColor': get_color_discrete_access(feature,var_name,min_communes,range_values),
                'fillOpacity': 1,
                'weight':0.1,
                },
                highlight_function=highlight_function).add_to(hec_group)

            m.fit_bounds(hec_group.get_bounds())

            for index, elem in enumerate(result_touches):
                if elem == True:
                    name_of_commune = gdf_communes.iloc[index].Nom_CMN
                    if name_of_commune != commune_request_name:
                        folium.GeoJson(gdf[gdf['name']==name_of_commune], 
                            name='geojson',
                            zoom_on_click=True,
                            tooltip=folium.GeoJsonTooltip(fields=['name', var_name]),
                            style_function= lambda feature:{
                            'fillColor': get_color_discrete_access(feature, var_name, min_communes, range_values),
                            'fillOpacity': 1,
                            'weight':0.1,
                            },
                            highlight_function=highlight_function).add_to(hec_group)

            hec_group.add_to(m)

            x_vect = [min_communes+range_values/10, min_communes+3*range_values/10, min_communes+5*range_values/10, min_communes+7*range_values/10, min_communes+9*range_values/10]
            width_vect = [range_values/5, range_values/5, range_values/5, range_values/5, range_values/5]
            color_vect = []

            for elem in x_vect:
                color_vect.append(get_color_access(elem,min_communes,range_values))

            data_tuples = list(zip(x_vect,width_vect,color_vect))

            df_test = pd.DataFrame(data_tuples, columns=['x','width','color'])

            fig = go.Figure(data=[go.Bar(
                x=df_test['x'],
                y=[1, 1, 1, 1, 1],
                marker={'color': df_test['color']},
                width=df_test['width']
            )])

            fig.update_yaxes(visible=False)

            config = {'staticPlot': True}

            set_layout(fig, min_communes, max_communes, 70, unit)

            fig.add_vline(x=mean_commune, line_width=2, line_color="blue")
            fig.add_annotation(x=mean_commune, y=0.5 , text="Moyenne communale", font=dict(size=12),showarrow=False,)

            legend_color_scale = fig.to_html(config=config)'''

        current_commune_text = commune_request_name+" - "+var_name + " " + unit

    folium.LayerControl().add_to(m)
    m = m._repr_html_()
    context = {

        'm' : m,
        'communes_names': communes_names,
        'list_env':list_env,
        'list_demo':list_demo,
        'list_accessibility':list_accessibility,
        'chart':chart,
        'hist':hist,
        'legend_color_scale':legend_color_scale,
        'legend_text':legend_text,
        'legend_moyenne_text':legend_moyenne_text,
        'current_commune_name':commune_request_name,
        'limitations_informations':limitations_informations,
        'current_commune_text' : current_commune_text,
        'var_name':var_name
    }

    return render(request, 'index.html', context)


def typologie(request):

    m = folium.Map(location = [46.61280022381356, 6.61517533257687],
        tiles=None,
        min_lat=46.2,max_lat=47.3,min_lon=5.9,max_lon=7.2, 
        zoom_start=9, max_zoom=15, min_zoom=9,
        zoom_control=False,
        )
    folium.TileLayer('cartodbpositron', control=False).add_to(m)

    highlight_function = lambda x: {
    'color': 'red', # stroke becomes red
    'opacity' : 0.9,
    'weight': 4,
    'dashArray' : '3, 6' # transforms the solid stroke to a dashed stroke
    }

    geojson_dir = geojson_dir = os.path.join(os.getcwd(),'geojson')
    colormap = linear.Set2_06.scale(1,9)

    typo_group = folium.FeatureGroup(name='Typologie')
    folium.GeoJson(os.path.join(geojson_dir,'Communes_WGS.geojson'), 
        name='geojson',
        zoom_on_click=True,
        overlay=False,
        tooltip=folium.GeoJsonTooltip(fields=['Nom_CMN', 'clust_ward'], aliases=['Nom de la commune','Classe de typologie']),
        style_function= lambda feature:{
        'fillColor': colormap(feature['properties']['clust_ward']),
        'fillOpacity': 0.8,
        'weight':1,
        },
        highlight_function=highlight_function).add_to(typo_group)
    typo_group.add_to(m)
    m.keep_in_front(typo_group)

    colors = ['#76d886','#a9975e','#e97c7c','#a9aac9','#c293d5','#e5b2e2','#a2e587','#d1f854','#e9e320']

    if request.method=="POST":

        m = folium.Map(location = [46.61280022381356, 6.61517533257687],
            tiles=None,
            min_lat=46.2,max_lat=47.3,min_lon=5.9,max_lon=7.2, 
            zoom_start=10, max_zoom=15, 
            min_zoom=9,
            zoom_control=False,
            )
        folium.TileLayer('cartodbpositron', control=False).add_to(m)

        category_numero = int(request.POST['category'])
        gdf = gpd.read_file(os.path.join(geojson_dir,'Communes_WGS.geojson'))
        gdf_sorted = gdf[gdf['clust_ward'] == category_numero]
        folium.GeoJson(gdf_sorted, 
            name='geojson',
            zoom_on_click=True,
            overlay=False,
            tooltip=folium.GeoJsonTooltip(fields=['Nom_CMN', 'clust_ward'], aliases=['Nom de la commune','Classe de typologie']),
            style_function= lambda feature:{
            'fillColor': colormap(category_numero),
            'fillOpacity': 0.8,
            'weight':1,
            },
            highlight_function=highlight_function).add_to(m)

    m = m._repr_html_()
    context={
        'm':m,
        'colors':colors,
    }

    return render(request, 'typologie.html', context)

def add_base_layers(m, highlight_function, geojson_dir):

    colormap = linear.Set2_06.scale(1,9)

    ################ COMMUNES ##############################################################
    communes_group = folium.FeatureGroup(name='Communes',control=False)
    folium.GeoJson(os.path.join(geojson_dir,'Communes_WGS.geojson'), 
        name='geojson',
        zoom_on_click=True,
        tooltip=folium.GeoJsonTooltip(fields=['Nom_CMN'], aliases=['Nom de la commune']),
        style_function= lambda feature:{
        'fillOpacity': 0,
        'weight':1,
        },
        highlight_function=highlight_function).add_to(communes_group)
    communes_group.add_to(m)

    ################ Typologie ##############################################################
    typo_group = folium.FeatureGroup(name='Typologie')
    folium.GeoJson(os.path.join(geojson_dir,'Communes_WGS.geojson'), 
        name='geojson',
        zoom_on_click=True,
        overlay=False,
        tooltip=folium.GeoJsonTooltip(fields=['Nom_CMN', 'clust_ward'], aliases=['Nom de la commune','Classe de typologie']),
        style_function= lambda feature:{
        'fillColor': colormap(feature['properties']['clust_ward']),
        'fillOpacity': 0.8,
        'weight':1,
        },
        highlight_function=highlight_function).add_to(typo_group)
    typo_group.add_to(m)
    m.keep_in_front(typo_group)

def add_base_places(m, geojson_dir):

    fg = MarkerCluster(name="Etablissements",show=False, disableClusteringAtZoom=14, control=False)
    m.add_child(fg)
    g = folium.plugins.FeatureGroupSubGroup(fg, "Ne pas afficher d'etablissement", overlay=False)
    m.add_child(g)

    etablissements_names = ['Pharmacies','Centre medico-social']
    etablissement_colors = ['green','red']
    etablissements_geojson = ['Pharmacies_WGS', 'CMS_WGS']

    for index_etablissement, etablissement in enumerate(etablissements_names):
        gdf = gpd.read_file(os.path.join(geojson_dir,etablissements_geojson[index_etablissement]+'.geojson'))
        g = folium.plugins.FeatureGroupSubGroup(fg, etablissement, overlay=False)
        m.add_child(g)
        cluster = MarkerCluster(name=etablissement)
        geo_df = [[point.xy[1][0], point.xy[0][0]] for point in gdf.geometry]

        for index, coordinates in enumerate(geo_df):
            
            if etablissement=='Pharmacies':
                iframe = folium.IFrame('<strong>Nom: </strong>' + str(gdf.NOM[index]) + '<br>' 
                                            + '<strong>Exploitant: </strong>' + str(gdf.EXPLOITANT[index]))

            if etablissement=='Centre medico-social':
                iframe = folium.IFrame('<strong>Nom: </strong>' + str(gdf.NOM[index]) + '<br>' 
                                    + '<strong>Exploitant: </strong>' + str(gdf.EXPLOITANT[index]))

            cluster.add_child(
                folium.Marker(
                    location = coordinates,
                    popup = folium.Popup(iframe, min_width=300, max_width=300),
                    icon=folium.Icon(icon='glyphicon-plus', color=etablissement_colors[index_etablissement]),
                )
            )
        cluster.add_to(g)

def set_layout(fig, min_canto, max_canto, height, var_name, unit):

    fig.update_layout(
        autosize=True,
        height=height,
        margin=dict(l=20, r=20, t=30, b=10),
        xaxis_range=[min_canto,max_canto],
        font=dict(size=10),
        title_font=dict(size=12),
        title_font_family="Helvetica Neue",
        title_font_color="black",
    )

    fig.update_xaxes(title=var_name+" "+unit, title_font = {"size": 10})

def set_layout_legend(fig, min_canto, max_canto):

    fig.update_layout(
        autosize=True,
        height=50,
        margin=dict(l=20, r=20, t=10, b=10),
        xaxis_range=[min_canto,max_canto],
        font=dict(size=10)
    )

def add_annotations(fig, x_1 ,x_2 ,x_3, x_4):

    fig.add_vline(x=x_1, line_width=1, line_dash="dash", line_color="black")
    fig.add_vline(x=x_2, line_width=1, line_dash="dash", line_color="black")
    fig.add_vline(x=x_3, line_width=1, line_dash="dash", line_color="black")
    fig.add_vline(x=x_4, line_width=1, line_dash="dash", line_color="black")


def set_x_values(x_min, x_1, x_2, x_3, x_4, x_max):
    x_list = [x_min, x_1, x_2, x_3, x_4, x_max]
    return x_list

def add_informations(df_test, x_list, mean_commune, gdf_kept, var_name, map_dict, x_text, href, unit, commune_name):

    ################### Legend Text ############################################################
    
    fig = go.Figure(data=[go.Bar(
        x=df_test['x'],
        y=[1, 1, 1, 1, 1],
        marker={'color': 'rgba(0,0,0,0)'},
        width=df_test['width'],
        marker_line_width = 0,
    )])
    fig.update_yaxes(visible=False)
    fig.update_xaxes(visible=False)

    fig.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

    add_legend_limitations_text(fig, x_list, x_text, href, y=0.25)

    config = {'staticPlot': True}

    fig.update_layout(
        autosize=True,
        height=30,
        margin=dict(l=20, r=20, t=5, b=0),
        xaxis_range=[x_list[0],x_list[5]],
    )

    legend_text = fig.to_html(config=config)

    ############ Legend ##############################################
    fig = go.Figure(data=[go.Bar(
                    x=df_test['x'],
                    y=[1, 1, 1, 1, 1],
                    marker={'color': df_test['color']},
                    width=df_test['width']
                )])

    fig.update_yaxes(visible=False)

    config = {'staticPlot': True}

    set_layout_legend(fig, x_list[0], x_list[5])

    add_annotations(fig, x_list[1], x_list[2], x_list[3], x_list[4])
    #fig.add_annotation(x=mean_commune, y=0.5 , text="Moyenne communale", font=dict(size=10),showarrow=False,)
    fig.add_vline(x=mean_commune, line_width=2, line_color="blue")

    legend_color_scale = fig.to_html(config=config)

    ########### moyenne communale #######################################

    fig = go.Figure(data=[go.Bar(
        x=df_test['x'],
        y=[1, 1, 1, 1, 1],
        marker={'color': 'rgba(0,0,0,0)'},
        width=df_test['width'],
        marker_line_width = 0,
    )])
    fig.update_yaxes(visible=False)
    fig.update_xaxes(visible=False)

    fig.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

    config = {'staticPlot': True}

    fig.update_layout(
        autosize=True,
        height=30,
        margin=dict(l=20, r=20, t=0, b=0),
        xaxis_range=[x_list[0],x_list[5]],
    )
    fig.add_annotation(x=mean_commune, y=1 , text="<b>Moyenne</b>", font=dict(size=10),showarrow=False,)
    fig.add_annotation(x=mean_commune, y=0.5 , text="<b>Communale</b>", font=dict(size=10),showarrow=False,)
    legend_moyenne_text = fig.to_html(config=config)

    ################### HISTOGRAM ########################################################

    fig = px.histogram(gdf_kept, x=var_name, range_x=[min(map_dict.values()),max(map_dict.values())], title=commune_name+" : Histogram des valeurs communales")

    add_annotations(fig, x_list[1], x_list[2], x_list[3], x_list[4])
    set_layout(fig, x_list[0], x_list[5], 200, var_name, unit)
    fig.update_yaxes(visible=False, showticklabels=False)

    hist = fig.to_html()

    ################### BOXPLOT ##########################################################

    fig = px.box(gdf_kept, x=var_name, range_x=[min(map_dict.values()),max(map_dict.values())], title=commune_name+" : boxplot des valeurs communales")

    add_annotations(fig, x_list[1], x_list[2], x_list[3], x_list[4])
    set_layout(fig, x_list[0], x_list[5], 200, var_name, unit)

    chart = fig.to_html()

    return legend_color_scale, legend_text, hist, chart, legend_moyenne_text

def select_var_lim_names(var_name):
    if var_name == "PM10":
        x_text = ["25 % Quantile","Mediane","WHO","Opair"]
        href = ["",
                "",
                """<a href="https://www.who.int/health-topics/air-pollution#tab=tab_1"><b>""",
                """<a href="https://www.fedlex.admin.ch/eli/cc/1986/208_208_208/fr"><b>"""]

    if var_name == "NOISE":
        x_text == ["No effect","slice effect","effect","dangerous situation"]
        href = ["","","","",""]

    return x_text, href

def add_legend_limitations_text(fig, x_list, x_text, href, y):
    if href[0] != "":
        fig.add_annotation(x=x_list[1], y=y , text=href[0]+x_text[0]+"""</b></a>""", font=dict(size=10),showarrow=False,)
    else:
        fig.add_annotation(x=x_list[1], y=y , text=x_text[0], font=dict(size=10),showarrow=False,)
    
    if href[1] != "":
        fig.add_annotation(x=x_list[2], y=y , text=href[1]+x_text[1]+"""</b></a>""", font=dict(size=10),showarrow=False,)
    else:
        fig.add_annotation(x=x_list[2], y=y , text=x_text[1], font=dict(size=10),showarrow=False,)

    if href[2] != "":
        fig.add_annotation(x=x_list[3], y=y , text=href[2]+x_text[2]+"""</b></a>""", font=dict(size=10),showarrow=False,)
    else:
        fig.add_annotation(x=x_list[3], y=y , text=x_text[2], font=dict(size=10),showarrow=False,)

    if href[3] != "":
        fig.add_annotation(x=x_list[4], y=y , text=href[3]+x_text[3]+"""</b></a>""", font=dict(size=10),showarrow=False,)
    else:
        fig.add_annotation(x=x_list[4], y=y , text=x_text[3], font=dict(size=10),showarrow=False,)


def get_color_discrete_access(feature, var_name, min, range):
    value = feature['properties'][var_name]
    if value is None:
        return '#8c8c8c'
    if value <= min+range/5:
        return ' #32ff6a '
    elif value <= min+2*range/5:
        return '#cdff32'
    elif value <= min+3*range/5:
        return '#f6ff32'
    elif value <= min+4*range/5:
        return '#ffca32'
    else:
        return '#ff0b0b'

def get_color_discrete(feature, var_name ,x1, x2, x3, x4 ):
    value = feature['properties'][var_name]
    if value is None:
        return '#8c8c8c'
    if value <= x1:
        return ' #32ff6a '
    elif value <= x2:
        return '#cdff32'
    elif value <= x3:
        return '#f6ff32'
    elif value <= x4:
        return '#ffca32'
    else:
        return '#ff0b0b' 

def get_color_access(val, min, range):
    value = val
    if value is None:
        return '#8c8c8c'
    if value <= min+range/5:
        return ' #32ff6a '
    elif value <= min+2*range/5:
        return '#cdff32'
    elif value <= min+3*range/5:
        return '#f6ff32'
    elif value <= min+4*range/5:
        return '#ffca32'
    else:
        return '#ff0b0b'

def get_color_discrete_value(val, x1, x2, x3, x4):
    value = val
    if value is None:
        return '#8c8c8c'
    if value <= x1:
        return ' #32ff6a '
    elif value <= x2:
        return '#cdff32'
    elif value <= x3:
        return '#f6ff32'
    elif value <= x4:
        return '#ffca32'
    else:
        return '#ff0b0b' 