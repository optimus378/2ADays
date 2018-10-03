import sharepy
import pymongo
from pymongo import MongoClient
import csv
import json
import random
import time
import datetime
import os
##Setup Database##
client = MongoClient()
db = client.twoadays
agentcol = db.agents
staffcol = db.staff
archivecol = db.archive

def syncSPList():
	s = sharepy.connect('https://kwaustin.sharepoint.com',"yourusername","yourpassword")
	r = s.get("https://kwaustin.sharepoint.com/am/_api/web/lists/GetByTitle('Agents')/Items?$select=Real_x0020_Estate_x0020_License_,FullName,CellPhone,Top20Percent&$filter=New_x0020_Agent_x0020_Status eq 'Active Agent' or New_x0020_Agent_x0020_Status eq 'New Agent'&$skiptoken=Paged=TRNE&$top=1000", headers={"accept": "application/json; odata=nometadata"})
	splist = r.json()
	spdict = splist['value']
	Ids = [i['Real_x0020_Estate_x0020_License_'] for i in spdict]
	FullName = [i['FullName'] for i in spdict]
	MobileNumber= [i['CellPhone'] for i in spdict]
	spdata = list(zip(Ids,FullName,MobileNumber,))
	for s in spdata:
		agentcol.find_one_and_update({'_id': s[0] },{'$set':{'agentname': s[1], 'mobilenumber':s[2], 'production': 'lower80',}},upsert=True)
	return


def getLastSync():
	agentcol.find({'lastSPSync'})
	return	

### STAFF FUNCTIONS ##
def addTL(name):
		staffcol.find_one_and_update({'name':name},{'$set':{'name':name,'TeamLeader':True}},upsert=True)
def removeTL(name):
		staffcol.find_one_and_update({'name':name},{'$set':{'name':name,'TeamLeader':False}},upsert=True)
def addStaff(name):
	staffcol.find_one_and_update({'name':name},{'$set':{'name':name, 'TeamLeader':False}},upsert=True)
def delStaff(name):
	staffcol.remove({'name':name})

def listStaff():
	staff = staffcol.find({'_id':{'$exists': True}})
	staffdict ={}
	for i in staff:
		remaining = agentcol.find({'$and':[{"StaffAssigned":i['name'] },{'currentInteraction':'None'}]}).count()
		totalcount = agentcol.find({"StaffAssigned":i['name']}).count()
		completed = str(totalcount - remaining)
		staffdict[i['name']] = (completed +' of ' + str(totalcount))
	return staffdict

def getagentlist(staffmember):   ## Gets list of agents assigned to Staff Member
	query = agentcol.find({"StaffAssigned":staffmember})
	agentlist = [i for i in query]
	return agentlist


def getagentstats(agentid): ## returns stats on individual agent
	agentstats = agentcol.find_one({'_id':agentid})
	return agentstats 
def updateagent(comment,agentid,interaction): ## adds comment underagentview 
	query = agentcol.find_one({'_id':agentid})
	date = datetime.datetime.now()
	staffname = query['StaffAssigned']
	agentcol.find_one_and_update({'_id':agentid},{'$push':{'comments':{'comment':comment,'date':date,'StaffName':staffname,'interaction':interaction}}})
	agentcol.find_one_and_update({'_id':agentid},{'$set':{'currentInteraction': interaction}})
	return
def splitlist():
	## Count staff and TLS
	staffcount = staffcol.find({'TeamLeader':False}).count()
	tlcount = staffcol.find({'TeamLeader':True}).count()
	## Get Names of Staff and TLS
	staffquery = staffcol.find({'TeamLeader':False})
	tlquery =  staffcol.find({'TeamLeader':True})
	stafflist = [i['name'] for i in staffquery]
	tlList = [i['name'] for i in tlquery]
	## Get list of Lower80 of Top20 and randomize and divide by staff and tl count
	lower80query= agentcol.find({'production': 'lower80'})
	lower80list = [i for i in lower80query]
	top20query = agentcol.find({'production': 'top20'})
	top20list = [i for i in top20query]
	random.shuffle(lower80list)
	random.shuffle(top20list)
	## Count the lower 80 agents and top20 Agents
	lower80 = agentcol.find({'production': 'lower80'},{'$exists': True}).count()
	#top20 = agentcol.find({'production': 'top20'},{'$exists': True}).count()
	## Divide lower80 by staff count, and top20 by TL Count
	lower80divided = round(lower80 / staffcount)
	top20divided = round(len(top20list) / tlcount)
	## Assign each split list to staff memebers. 
	lcount = 0 
	while lcount < staffcount:
		x = lcount * lower80divided
		y = (lcount + 1) * lower80divided
		lower80split = lower80list[x : y]
		for z in lower80split:
			agentcol.find_one_and_update({"_id": z['_id']},{"$set":{"StaffAssigned":stafflist[lcount]}},upsert=True)
		lcount = lcount+1
	## get DB of top20 randomize and split between TLS
	tcount = 0 
	while tcount < tlcount:
		x = tcount * top20divided
		y = (tcount+1) * top20divided
		top20split= top20list[x:y]
		for z in top20split:
			agentcol.find_one_and_update({"_id": z['_id']},{"$set":{"StaffAssigned":tlList[tcount]}},upsert=True)
		tcount = tcount +1
	agentcol.update_many({},{'$set':{'currentInteraction':'None'}},upsert=True)

def importTop20(filename):
	f = open(filename,'r')
	reader = csv.DictReader( f, fieldnames = ( "FirstName","LastName","REA Number"))  
	out = json.dumps( [ row for row in reader ] )
	jsonload = json.loads(out)
	## Strip leading Zero from Lic Number
	for i in jsonload:
			if len(i['REA Number']) is 7:
				print("Before: " + i['REA Number'])
				i['REA Number'] = i['REA Number'][1:]
    ## remove rows with no LIC Number
	for i in jsonload:
		if i['REA Number'] is "":
			print("Agent has blank REA Number in MORE and was removed from import. " +  i['FirstName'] + " " +i['LastName'])
			jsonload.remove(i) 
	## Run again because it sucks for some reason. 
	for i in jsonload:
		if i['REA Number'] is "":
			print("Agent has blank REA Number in MORE and was removed from import. " +  i['FirstName'] + " " +i['LastName'])
			jsonload.remove(i) 
	## Sync MORE LIST -->> with DATABASE
	dbIDS = [i['_id'] for i in agentcol.find({},{'_id':1})]
	moreIDS = [i['REA Number'] for i in jsonload]
	archivedAgents = []
	for i in dbIDS:
		if i not in moreIDS:
				agentToArchive= agentcol.find_one({'_id':i})
				try:
					archivecol.insert_one(agentToArchive)
					agentcol.delete_one({'_id':i})
					print('archived ' + agentToArchive['agentname'])
					archivedAgents.append(agentToArchive['agentname'])
				except:
					print('Already in Archive ' + agentToArchive['agentname'])
					archivedAgents.append(agentToArchive['agentname'] + ' - Already Archived')
					agentcol.delete_one({'_id':i})
		continue
	## take top20 percent of gci list 
	moretwentypercent = round(float(0.20)*len(jsonload)) +1
	moretop20list = jsonload[0:moretwentypercent]
	## Find Existing top20 Agents in Database and compare with new MORE Top 20 List.
	top20dbquery = agentcol.find({'production':'top20'})
	dbtop20 = []
	for i in top20dbquery:
		dbtop20.append(i)  
	## If Agent is no longer in top 20 from new Morelist, change to lower80
	for i in dbtop20:
		if i['production'] not in moretop20list:
			agentcol.find_one_and_update({'_id':i},{'$set':{'production':'lower80'}})
	## If agent is in new More top20 list, change to production to top20
	for i in moretop20list:
		agentcol.find_one_and_update({'_id':i['REA Number']},{'$set':{'production':'top20'}})
	f.close()
	os.remove(filename)
	return archivedAgents

def exportlists(name):
	query = agentcol.find({"StaffAssigned": name})
	csvout = [i for i in query]
	##agentname = [i['agentname'] for i in csvout]
	##mobilenumber = [i['mobilenumber'] for i in csvout]
	##csvdata = list(zip(agentname, mobilenumber))
	fnames = ["Agent Name", "Mobile","Date","Talked To", "Voicemail", "List for: "  + name ]
	with open('%s.csv' %name, 'w') as f:
		writer = csv.DictWriter(f, fieldnames=fnames, delimiter = ',' , lineterminator='\n') 
		writer.writeheader()
		for i in csvout:
			writer.writerow({'Agent Name' : i['agentname'], 'Mobile': i['mobilenumber']})
		return

## Send Text ##
##def sendSms( id, number):