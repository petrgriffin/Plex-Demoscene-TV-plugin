import re, sys, datetime
from operator import itemgetter
from PMS import Plugin, Log, DB, Thread, XML, HTTP, JSON, RSS, Utils
from PMS.MediaXML import MediaContainer, DirectoryItem, WebVideoItem, VideoItem, SearchDirectoryItem
from PMS.Shorthand import _L, _R

DEBUG=1

DTV_PLUGIN_PREFIX   = "/video/demoscene.tv"
DTV_ROOT_URL        = "http://www.demoscene.tv"
DTV_FEATURED = DTV_ROOT_URL 
DTV_LAST_ADDED = DTV_ROOT_URL + "/page.php?id=172&lang=uk&vsmaction=listingLastAddedProd"
DTV_LAST_RELEASED = DTV_ROOT_URL + "/page.php?id=172&vsmaction=listingLastReleasedProd"
DTV_TOP_WEEK= DTV_ROOT_URL + "/page.php?id=172&lang=uk&vsmaction=listingTopWeekViewedProd"
DTV_TOP_MONTH = DTV_ROOT_URL + "/page.php?id=172&lang=uk&vsmaction=listingTopMonthViewedProd"
DTV_TOP_ALLTIME = DTV_ROOT_URL + "/page.php?id=172&lang=uk&vsmaction=listingTopAlltimeViewedProd"
DTV_TOP_RATING = DTV_ROOT_URL + "/page.php?id=172&lang=uk&vsmaction=listingTopRatingProd"

#streaming doesn't work with Plex
DTV_STREAMING_PARAM = "&dontusestreaming=1"

DTV_JSON_URL = DTV_ROOT_URL + "/getJSON.php"
DTV_FEED_LENGTH = 100
TITLE_CUT_PHRASE = "Demoscene.tv "

LISTS_CACHE_TIMEOUT = 600
ENTRY_CACHE_TIMEOUT = 3600
SHORT_CACHE_TIMEOUT = 10

grouplist = {}

####################################################################################################
def Start():
  Plugin.AddRequestHandler(DTV_PLUGIN_PREFIX, HandleVideosRequest, "demoscene.tv", "icon-default.png", "art-default.png")
  Plugin.AddViewGroup("Details", viewMode="InfoList", contentType="episode") 
####################################################################################################

def Debug(var_name, var):
  if DEBUG == 1:
    Log.Add("Debug: " + var_name + " -> " + str(var))  
  
def WhatIsDemoScene():
  thumbUrl = "http://dtv.was.demoscene.tv/was/app/demoscenetv/14/wid.jpg"
  desc = "Report by demscene.tv [DTV]"
  title = "What Is Demoscene?"
  videoUrl = "http://flvvod202530.demoscene.tv/getvideo.php?file=1730_12573_demoscene.tv_what_is_demoscene__wid__report__flash.flv"
  return VideoItem(videoUrl, title, desc, "", thumbUrl)

####################################################################################################
# new JSON-based data query   

def Cached(url, force=False):
  return JSON.DictFromString(HTTP.GetCached(url, LISTS_CACHE_TIMEOUT, force))


def GetJsonQuery(query, length=0):
  param = ""
  if length > 0:
    param = param + "&num=" + str(length) + DTV_STREAMING_PARAM
  url = DTV_JSON_URL + "?type=" + query + param
  object = Cached(url)
  Debug("Retrieved Feed:", object["title"] + ": " + object["description"]) 
  Debug("Feed URL: ", url)
  Debug("JSON object: ", object)
  return object


def GetJsonQueryTitle(feed):
  object = GetJsonQuery(feed, 1)
  if "title" in object:
    return re.sub(TITLE_CUT_PHRASE, "",object["title"])
  else:
    return "not found"
    
    
def GetJsonQueryDescription(feed):
  object = GetJsonQuery(feed, 1)
  if "description" in object:
    return object["description"]
  else:
    return "not found"


def GetValue(key, item):
  if key in item:
    value = item[key]
  else:
    value = "n/a"
  Debug("Entry " + key + ": ", value)
  return value   
  
  
def GetFeedDirectory(feed):
  feed = GetJsonQuery(feed, DTV_FEED_LENGTH)
  dir = MediaContainer("art-default.png", title1="demoscene.tv", title2=re.sub(TITLE_CUT_PHRASE, "", GetValue("title", feed)))
  
  for item in feed["items"]:
    try:
      title = re.sub(TITLE_CUT_PHRASE, "", GetValue("title", item))
      videoUrl = GetValue("videofile", item)
      creator = GetValue("creator", item)
      category = GetValue("category", item)
      thumbUrl = GetValue("screenshot", item)
      desc = "Demogroup:\t" + creator + "\n\nPlatform:\t" + category
      
      dir.AppendItem(VideoItem(videoUrl, title, desc, "", thumbUrl))
    
    except:
      Log.Add("Failed to load entry!")
      
  return dir


def GetList(listname):
  result = GetJsonQuery(listname)
  list = result["items"]
  
  dir = MediaContainer("art-default.png", title1="demoscene.tv", title2=GetJsonQueryTitle(listname))
  for id, name in list:
    Debug("item: ", id +"->" + name)
    dir.AppendItem(DirectoryItem(id, name, _R("icon-default.png"), name))
  
  return dir

def GetPartyYears(id):
  result = GetJsonQuery("partyyears&id_party=" + id)
  dir = MediaContainer("art-default.png", title1="demoscene.tv", title2=GetJsonQueryTitle("partyyears&id_party=" + id))
  dir.AppendItem(DirectoryItem("all_years", "all years", _R("icon-default.png"), "all years"))
  for item in result["items"]:
    dir.AppendItem(DirectoryItem(item, item, _R("icon-default.png"), item))
  return dir

####################################################################################################
# Build the menues
####################################################################################################

def Index():
  dir = MediaContainer("art-default.png", "Details", "demoscene.tv")
  dir.AppendItem(DirectoryItem("cat/lastadded", GetJsonQueryTitle("lastadded"), _R("icon-default.png"), GetJsonQueryDescription("lastadded")))
  dir.AppendItem(DirectoryItem("cat/lastreleased", GetJsonQueryTitle("lastreleased"), _R("icon-default.png"), GetJsonQueryDescription("lastreleased")))
  dir.AppendItem(DirectoryItem("cat/topweek", GetJsonQueryTitle("topweek"), _R("icon-default.png"), GetJsonQueryDescription("topweek")))
  dir.AppendItem(DirectoryItem("cat/topmonth", GetJsonQueryTitle("topmonth"), _R("icon-default.png"), GetJsonQueryDescription("topmonth")))
  dir.AppendItem(DirectoryItem("cat/alltimetop", GetJsonQueryTitle("alltimetop"), _R("icon-default.png"), GetJsonQueryDescription("alltimetop")))
  dir.AppendItem(DirectoryItem("cat/toprating", GetJsonQueryTitle("toprating"), _R("icon-default.png"), GetJsonQueryDescription("toprating")))
  dir.AppendItem(DirectoryItem("cat/groups", GetJsonQueryTitle("listofgroups"), _R("icon-default.png"), GetJsonQueryDescription("listofgroups")))
  dir.AppendItem(DirectoryItem("cat/parties", GetJsonQueryTitle("listofparties"), _R("icon-default.png"), GetJsonQueryDescription("listofparties")))
  dir.AppendItem(WhatIsDemoScene())
  return dir
  
def HandleVideosRequest(pathNouns, count):
  dir = MediaContainer("art-default.png", "", "")
  if count == 0:
    dir = Index()
    
  elif count > 3: 
    if pathNouns[1] == "parties":
      if pathNouns[3] == "all_years":
        dir = GetFeedDirectory("lastreleased&party=" + pathNouns[2])
      else:
        dir = GetFeedDirectory("lastreleased&party=" + pathNouns[2] + "&yearofparty=" + pathNouns[3]) 
      
  elif count > 2:  
    if pathNouns[1] == "groups": 
      dir = GetFeedDirectory("lastreleased&group=" + pathNouns[2])  
    elif pathNouns[1] == "parties":
      dir = GetPartyYears(pathNouns[2]);  
      
  elif count > 1:
    Debug("pathNouns, count",  pathNouns[0] +"/"+ pathNouns[1] +", "+ str(count))
    if pathNouns[1] == "lastadded":
      dir = GetFeedDirectory("lastadded")
    elif pathNouns[1] == "lastreleased":
      dir = GetFeedDirectory("lastreleased")
    elif pathNouns[1] == "topweek":
      dir = GetFeedDirectory("topweek")
    elif pathNouns[1] == "topmonth":
      dir = GetFeedDirectory("topmonth")
    elif pathNouns[1] == "alltimetop":
      dir = GetFeedDirectory("alltimetop")
    elif pathNouns[1] == "toprating":
      dir = GetFeedDirectory("alltimetop")
    elif pathNouns[1] == "groups": 
      dir = GetList("listofgroups")
    elif pathNouns[1] == "parties": 
      dir = GetList("listofparties")

  return dir.ToXML()