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
    

def Index():
  dir = MediaContainer("art-default.png", "Details", "demoscene.tv")
  #dir.AppendItem(FeaturedEntry(DTV_FEATURED))
  dir.AppendItem(DirectoryItem("cat/lastadded", "Last added productions", _R("icon-default.png")))
  dir.AppendItem(DirectoryItem("cat/lastreleased", "Latest released productions", _R("icon-default.png")))
  dir.AppendItem(DirectoryItem("cat/topweek", "Top week viewed productions", _R("icon-default.png")))
  dir.AppendItem(DirectoryItem("cat/topmonth", "Top month viewed productions", _R("icon-default.png")))
  dir.AppendItem(DirectoryItem("cat/topalltime", "Top all time viewed productions", _R("icon-default.png")))
  dir.AppendItem(DirectoryItem("cat/toprating", "Top rated productions", _R("icon-default.png")))
  dir.AppendItem(WhatIsDemoScene())
  
  return dir  


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
  
  
def RandomEntry(url):
  xml = XML.ElementFromString(HTTP.GetCached(url, SHORT_CACHE_TIMEOUT), True)
  
  element = xml.xpath('//font[@class="vsm_viewcurrentprodscreenshot"]/a')[0]
  Debug("Element XML", XML.html.tostring(element));
  thumbUrl = element.xpath('./img')[0].get("src")
  Debug("thumbnail URL", thumbUrl)
  desc = element.xpath('./img')[0].get("alt")
  Debug("description", desc)
  title = "Random Demo"
  Debug("title", title)
  videoUrl = DTV_ROOT_URL + "/" + element.get("href")
  Debug("videopage URL", videoUrl)
  return WebVideoItem(videoUrl, title, desc, "", thumbUrl)

def WhatIsDemoScene():
  thumbUrl = "http://dtv.was.demoscene.tv/was/app/demoscenetv/14/wid.jpg"
  desc = "Report by demscene.tv [DTV]"
  title = "What Is Demoscene?"
  videoUrl = "http://flvvod202530.demoscene.tv/demoscene.tv_what_is_demoscene__wid__report__flash.flv"
  return VideoItem(videoUrl, title, desc, "", thumbUrl)

def HandleVideosRequest(pathNouns, count):
  dir = MediaContainer("art-default.png", "", "")
  if count == 0:
    dir = Index()
    
  elif count > 1:
    if pathNouns[1] == "lastadded":
      dir = ListEntries(DTV_LAST_ADDED, "Last Added")
    elif pathNouns[1] == "lastreleased":
      dir = ListEntries(DTV_LAST_RELEASED, "Last Released")
    elif pathNouns[1] == "topweek":
      dir = ListEntries(DTV_TOP_WEEK, "Top Week")
    elif pathNouns[1] == "topmonth":
      dir = ListEntries(DTV_TOP_MONTH, "Top Month")
    elif pathNouns[1] == "topalltime":
      dir = ListEntries(DTV_TOP_ALLTIME, "Top All Time")
    elif pathNouns[1] == "toprating":
      dir = ListEntries(DTV_TOP_RATING, "Top Rating")  
  
  return dir.ToXML()
