import re, sys, datetime
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

LISTS_CACHE_TIMEOUT = 600
ENTRY_CACHE_TIMEOUT = 3600
SHORT_CACHE_TIMEOUT = 10

####################################################################################################
def Start():
  Plugin.AddRequestHandler(DTV_PLUGIN_PREFIX, HandleVideosRequest, "demoscene.tv", "icon-default.png", "art-default.png")
  Plugin.AddViewGroup("Details", viewMode="InfoList", contentType="episode") 
####################################################################################################

def Debug(var_name, var):
  if DEBUG == 1:
    Log.Add("Debug: " + var_name + " -> " + str(var))  


def GetReleaseDescription(element):
  elems = element.xpath('.//a[@target="_blank"]')
  if len(elems) > 0:
    desc = "by " + elems[0].text
  else:
    desc = "by unknown artist"

  return desc

def GetPlatform(elememt):
  elems = element.xpath('.//font[@class="vsm_viewcurrentprodplateforme"]')
  platform = "on unknown platform"
  if len(elems) > 0:
    platform = elems[0].text
  
  return platform
  
  
def GetThumbnailUrl(element):
  thumbUrl = element.xpath('./td/a/img[contains(@name, "IMG")]')[0].get("src")
  
  return thumbUrl


def GetReleaseTitle(element):
  title = element.xpath('./td/font[@class="vsm_viewcurrentprodtitle"]/a')[0].text
  
  return title


def GetReleaseDetailPageUrl(element):
  url = DTV_ROOT_URL + "/"+ element.xpath('./td/a')[0].get("href")
  
  return url

  
def GetItemDescription(element):
  Debug("ReleaseEntry XML", XML.html.tostring(element));
  thumbUrl = GetThumbnailUrl(element)
  Debug("thumbnail URL", thumbUrl)
  desc = GetReleaseDescription(element)
  Debug("description", desc)
  title = GetReleaseTitle(element)
  Debug("title", title)
  detailPageUrl = GetReleaseDetailPageUrl(element)
  Debug("videopage URL", detailPageUrl)
  return GetVideoItem(detailPageUrl, title, desc, thumbUrl)  
  

def GetVideoItem(url, title, description, thumbUrl):

  Debug("Release URL", url);
  xml = XML.ElementFromString(HTTP.GetCached(url, ENTRY_CACHE_TIMEOUT), True)
  quality = "unknown"
  
  # Get Video URLs by hrefs
  elements = xml.xpath('.//font[@class="vsm_viewprodfile"]')
  Debug(" Detail XML", XML.html.tostring(elements[0]))
  videoUrl = url
  links= elements[0].xpath('./a')
  for link in links:
    href = link.get("href")
    Debug("href", href)
    
    # Parse video URLs from href strings and decide best quality
    videoUrls = href.split("'")
    for vidUrl in videoUrls:
      Debug("videoUrl", videoUrl)
      if vidUrl.endswith("mp4"):
        videoUrl = vidUrl
        quality = "HD"
        break
      elif vidUrl.endswith("flv"):
        videoUrl = vidUrl
        quality = "SD"
  
  Debug("quality", quality)
  Debug("videoUrl", videoUrl)
  
  if quality == "HD" or quality == "SD":
    return VideoItem(videoUrl, title + " ("+ quality +")", description, "", thumbUrl)
  else:
    return WebVideoItem(url, title +" (flash)", description, "", thumbUrl)

  
def ListEntries(url, dirname):
  dir = MediaContainer("art-default.png", title1="demoscene.tv", title2=dirname)
  xml = XML.ElementFromString(HTTP.GetCached(url, LISTS_CACHE_TIMEOUT), True)

  for item in xml.xpath('//table[@class="vsmmainproductiontable"]/tr'):
    if len(item.xpath('./td/a/img[contains(@name, "IMG")]')) > 0:
      dir.AppendItem(GetItemDescription(item))
    
  return dir  
  
  
def WhatIsDemoScene():
  thumbUrl = "http://dtv.was.demoscene.tv/was/app/demoscenetv/14/wid.jpg"
  desc = "Report by demscene.tv [DTV]"
  title = "What Is Demoscene?"
  videoUrl = "http://flvvod202530.demoscene.tv/demoscene.tv_what_is_demoscene__wid__report__flash.flv"
  return VideoItem(videoUrl, title, desc, "", thumbUrl)

####################################################################################################
# new JSON-based feed retrieval   

def Cached(url, force=False):
  return JSON.DictFromString(HTTP.GetCached(url, LISTS_CACHE_TIMEOUT, force))


def GetJsonFeed(feed, length):
  object = Cached(DTV_JSON_URL + "?type=" + feed + "&num=" + str(length) + DTV_STREAMING_PARAM)
  Debug("Feed URL: ", DTV_JSON_URL + str(id) + DTV_STREAMING_PARAM)
  Debug("JSON object: ", object)
  title = object["title"]
  description = object["description"]
  Debug("Feed:", title + ": " + description) 
  return object

def GetJsonFeedTitle(feed):
  object = GetJsonFeed(feed, 1)
  if "title" in object:
    return object["title"]
  else:
    return "not found"
    
    
def GetJsonFeedDescription(feed):
  object = GetJsonFeed(feed, 1)
  if "title" in object:
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
  feed = GetJsonFeed(feed, DTV_FEED_LENGTH)
  dir = MediaContainer("art-default.png", title1="demoscene.tv", title2=GetValue("title", feed))
  
  for item in feed["items"]:
    try:
      title = GetValue("title", item)
      videoUrl = GetValue("videofile", item)
      creator = GetValue("creator", item)
      category = GetValue("category", item)
      thumbUrl = GetValue("screenshot", item)
      desc = "Demogroup:\t" + creator + "\n\nPlatform:\t" + category
      Debug("Entry Desc: ", desc)
      
      dir.AppendItem(VideoItem(videoUrl, title, desc, "", thumbUrl))
    except:
      Log.Add("Failed to load entry!")
      
  Debug("dir", dir)
  return dir

####################################################################################################
# Build the menues

def Index():
  dir = MediaContainer("art-default.png", "Details", "demoscene.tv")
  dir.AppendItem(DirectoryItem("cat/lastadded", GetJsonFeedTitle("lastadded"), _R("icon-default.png"), GetJsonFeedDescription("lastadded")))
  dir.AppendItem(DirectoryItem("cat/lastreleased", GetJsonFeedTitle("lastreleased"), _R("icon-default.png"), GetJsonFeedDescription("lastreleased")))
  dir.AppendItem(DirectoryItem("cat/topweek", "Top week viewed productions", _R("icon-default.png")))
  dir.AppendItem(DirectoryItem("cat/topmonth", "Top month viewed productions", _R("icon-default.png")))
  dir.AppendItem(DirectoryItem("cat/topalltime", "Top all time viewed productions", _R("icon-default.png")))
  dir.AppendItem(DirectoryItem("cat/toprating", "Top rated productions", _R("icon-default.png")))
  dir.AppendItem(WhatIsDemoScene())
  return dir
  
def HandleVideosRequest(pathNouns, count):
  dir = MediaContainer("art-default.png", "", "")
  if count == 0:
    dir = Index()
    
  elif count > 1:
    if pathNouns[1] == "lastadded":
      dir = GetFeedDirectory("lastadded")
    elif pathNouns[1] == "lastreleased":
      dir = GetFeedDirectory("lastreleased")
    elif pathNouns[1] == "topweek":
      dir = ListEntries(DTV_TOP_WEEK, "Top Week")
    elif pathNouns[1] == "topmonth":
      dir = ListEntries(DTV_TOP_MONTH, "Top Month")
    elif pathNouns[1] == "topalltime":
      dir = ListEntries(DTV_TOP_ALLTIME, "Top All Time")
    elif pathNouns[1] == "toprating":
      dir = ListEntries(DTV_TOP_RATING, "Top Rating")
  
  return dir.ToXML()
