#!/usr/bin/env python

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import re,getopt,sys

def usage():
    print("usage: StatsGen.py -o <oligo info file> -s <site name>")


oligo_file = ""
key = ""

try:
    opts, args = getopt.getopt(sys.argv[1:], 'o:s:h',)
except getopt.GetoptError:
    usage()
    sys.exit(2)
    
if not opts:
    usage()
    sys.exit(2)
else:
    for opt, arg in opts:
        if opt == '-h':
            usage()
            sys.exit(2)
        elif opt == '-o':
            oligo_file = arg
        elif opt == '-s':
            key = arg
        else:
            usage()
            sys.exit(2)

colourDict = {}
#df = pd.read_table("/t1-data1/WTSA_Dev/jkerry/CaptureC/CRISPR-OT/AllOligos_Info.txt",sep="\t")
df = pd.read_table(oligo_file,sep="\t")

#print(df[:25])

### Define colour codes
#Counter = 0.3
#for i in df['Site'].unique():
#    colourDict[i] = Counter
#    Counter=Counter+0.3
#
### Add colour list codes to dataframe    
#CodeList = []
#for i in df['Site']:
#    CodeList.append(colourDict[i])
#df['Colour code'] = CodeList


## Add sizes/(number from cut-site) to dataframe
NumberList = []
#SiteList = []

#for i in df.index.values:
#    #NumberList.append(16-int(re.search(r'\d+',df.iloc[i]['Location']).group(0)))
#    if df.iloc[i]['Location'][:2]=="Up":
#        SiteList.append(-1*int(df.iloc[i]['Distance from site (bp)']))
#    else:
#        SiteList.append(int(df.iloc[i]['Distance from site (bp)']))
        
group_df = df.groupby('Site')
    
SiteList = []
for i in group_df.get_group(key).index.values:
    if df.iloc[i]['Location'][:2]=="Up":
        SiteList.append(-1*int(df.iloc[i]['Distance from site (bp)']))
    else:
        SiteList.append(int(df.iloc[i]['Distance from site (bp)']))


fig, ax = plt.subplots()
ColourList = np.where(group_df.get_group(key)['Repeat length']<(len(group_df.get_group(key)['Sequence'])/4),'b','r')
plt.scatter(SiteList,group_df.get_group(key)['Density score'],c=ColourList,s=[x+10 for x in group_df.get_group(key)['Repeat length']])

ax.set_xlabel('Distance from cut site (bp)')
ax.set_ylabel('STAR Density Score',rotation=0)

ax.spines['left'].set_position('zero')
ax.spines['right'].set_color('none')
ax.spines['bottom'].set_position('zero')
ax.spines['top'].set_color('none')
#ax.spines['left'].set_smart_bounds(True)
#ax.spines['bottom'].set_smart_bounds(True)
ax.xaxis.set_ticks_position('bottom')
ax.yaxis.set_ticks_position('left')
plt.tick_params(axis='both', labelsize=11)
plt.title(key,y=1.07, fontsize=18, fontweight='bold')
ax.yaxis.set_label_coords(0.5,1.02)
ax.set_xlim(min(SiteList)-10,max(SiteList)+10)
ax.set_ylim(0,max(group_df.get_group(key)['Density score'])+10)
#FigName = "Distribution"+str(Counter)+".png"
plt.plot([100,100],[0,max(group_df.get_group(key)['Density score'])+10], 'k--', lw=1)
plt.plot([-100,-100],[0,max(group_df.get_group(key)['Density score'])+10], 'k--', lw=1)
plt.plot([min(SiteList)-10,max(SiteList)+10],[50,50], 'r--', lw=1)
for i, txt in enumerate(group_df.get_group(key)['Location']):
    ax.annotate(txt,(SiteList[i],group_df.get_group(key).reset_index()['Density score'][i]), fontsize=11)
plt.subplots_adjust(bottom=0.15) 
#plt.savefig(FigName)
plt.show()



#for key, item in group_df:
#    
#    SiteList = []
#    for i in group_df.get_group(key).index.values:
#    #NumberList.append(16-int(re.search(r'\d+',df.iloc[i]['Location']).group(0)))
#        if df.iloc[i]['Location'][:2]=="Up":
#            SiteList.append(-1*int(df.iloc[i]['Distance from site (bp)']))
#        else:
#            SiteList.append(int(df.iloc[i]['Distance from site (bp)']))
#    
#    #print(key,item)
#    fig, ax = plt.subplots()
#    ColourList = np.where(group_df.get_group(key)['Repeat length']>30,'r','b')
#    #plt.scatter(SiteList,group_df.get_group(key)['Density score'],c=cm.rainbow(group_df.get_group(key)['Colour code']),s=[x+10 for x in group_df.get_group(key)['Repeat length']])
#    plt.scatter(SiteList,group_df.get_group(key)['Density score'],c=ColourList,s=[x+10 for x in group_df.get_group(key)['Repeat length']])
#    
#    ax.set_xlabel('Distance from cut site (bp)')
#    ax.set_ylabel('STAR Density Score',rotation=0)
#    
#    ax.spines['left'].set_position('zero')
#    ax.spines['right'].set_color('none')
#    ax.spines['bottom'].set_position('zero')
#    ax.spines['top'].set_color('none')
#    #ax.spines['left'].set_smart_bounds(True)
#    #ax.spines['bottom'].set_smart_bounds(True)
#    ax.xaxis.set_ticks_position('bottom')
#    ax.yaxis.set_ticks_position('left')
#    plt.tick_params(axis='both', labelsize=8)
#    plt.title(key,y=1.07, fontsize=14, fontweight='bold')
#    ax.yaxis.set_label_coords(0.5,1.02)
#    ax.set_xlim(min(SiteList)-10,max(SiteList)+10)
#    ax.set_ylim(0,max(group_df.get_group(key)['Density score'])+10)
#    FigName = "Distribution"+str(Counter)+".png"
#    plt.plot([100,100],[0,max(group_df.get_group(key)['Density score'])+10], 'k--', lw=1)
#    plt.plot([-100,-100],[0,max(group_df.get_group(key)['Density score'])+10], 'k--', lw=1)
#    plt.plot([min(SiteList)-10,max(SiteList)+10],[50,50], 'r--', lw=1)
#    for i, txt in enumerate(group_df.get_group(key)['Location']):
#        #print(i,txt)
#        ax.annotate(txt,(SiteList[i],group_df.get_group(key).reset_index()['Density score'][i]), fontsize=8)
#        #print(group_df.get_group(key)['Density score'][i])
#        #ax.annotate(txt,(SiteList[i],SiteList[i]))
#    plt.subplots_adjust(bottom=0.15) 
#    plt.savefig(FigName)
#    #plt.show()
#    Counter+=1

#fig, ax = plt.subplots()
#plt.scatter(SiteList,df['Density score'],c=cm.rainbow(df['Colour code']),s=[x+10 for x in df['Repeat length']])
#
#ax.set_xlabel('Distance from cut site (bp)')
#ax.set_ylabel('STAR Density Score')
#
#ax.spines['left'].set_position('zero')
#ax.spines['right'].set_color('none')
#ax.spines['bottom'].set_position('zero')
#ax.spines['top'].set_color('none')
##ax.spines['left'].set_smart_bounds(True)
##ax.spines['bottom'].set_smart_bounds(True)
#ax.xaxis.set_ticks_position('bottom')
#ax.yaxis.set_ticks_position('left')
#
#ax.set_xlim(min(SiteList)-10,max(SiteList)+10)
#ax.set_ylim(0,max(df['Density score'])+10)

#plt.show()
#plt.savefig('Distribution.png')