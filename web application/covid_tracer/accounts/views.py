from django.http import request
from django.http.response import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from accounts.models import LocalCommunity, RegisteredUser, Profile, TraceLocation, DeviceSessions
from django.contrib.auth.models import auth


import cv2
import pytesseract
import numpy as np
from django.core.files.storage import FileSystemStorage

import random
from django.core.cache import cache
from django.db import connection
import json
import string

from django.http import JsonResponse
from django.core import serializers

def login(request):

    if request.method=='POST':
        
        status, secs = throttle(request, 's')
        if status:
            messages.error(request, 'Maximum Rate Exceeded. Wait for '+str(secs)+'s')
            return redirect('login')
        
        username = request.POST['username']
        pswrd = request.POST['password']

        user = auth.authenticate(username=username, password=pswrd)

        if user is not None:
            
            throttle(request, 'd')
            auth.login(request, user)

            #check if phone is verified
            profile = Profile.objects.get(user=user)
            if not profile.is_verified:
                return redirect('otp')
            
            else:
                if request.POST.get('remember-me'):
                    # sesssion valid for 2 weeks
                    request.session.set_expiry(1209600)

                if request.COOKIES.get('token'):
                    token = request.COOKIES['token']
                    # check if the token is valid
                    request.session['username'] = username
                    return redirect('home')
                
                else:
                    return redirect('otp')

        else:
            messages.error(request, 'Invalid Credentials')
            return redirect('login')

    else:
        
        #if 'username' in request.session:
        #   if request.user.is_authenticated and request.session['username']==request.user.username:
        #        return redirect('home')
            
        #else:
        #    return render(request, 'login.html')

        return render(request, 'login.html')
        
    

def register(request):

    if request.method=='POST':

        status, secs = throttle(request, 's')
        if status:
            messages.error(request, 'Maximum Rate Exceeded. Wait for '+str(secs)+'s')
            return redirect('register')

        else:

            nic = request.POST['nic']
            try:
                nic2 = LocalCommunity.objects.get(nic=nic)
            except:
                lc = LocalCommunity(nic=nic)
                lc.save()

            try:
                RegisteredUser.objects.get(nic=LocalCommunity.objects.get(nic=nic2))
                messages.error(request, "User already exists")
                return redirect('register')
            except:
                pass
            
            
            img_nic = request.FILES['nicimg']
            filestr = img_nic.read()
            npimg = np.fromstring(filestr, np.uint8)
            img = cv2.imdecode(npimg, cv2.IMREAD_UNCHANGED)

            fs = FileSystemStorage()
            name = fs.save(str(img_nic), img_nic)
            url = fs.url(name)

            #img = cv2.imread("nic.jpg")
            gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
            gray = cv2.medianBlur(gray,5)
            th, threshed = cv2.threshold(img,127,255,cv2.THRESH_TRUNC)
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            result = pytesseract.image_to_string((threshed),lang="eng")
            for word in result.split("\n"):
                for lst in word.split(" "):    
                    if lst.startswith("19",0,2) or lst.startswith("20",0,2): 
                        if (lst==nic):  
                            throttle(request, 'd')
                            request.session['nic'] = nic
                            return redirect('confirm')
                        else:
                            #messages.error(request, "Couldn't verify your identity")
                            #return redirect('register')
                            request.session['nic'] = nic
                            return redirect('confirm')
                    
    else:
        return render(request, 'register.html')



def confirm(request):

    if request.method=='POST':

        nicid = request.session['nic']
        nic = LocalCommunity.objects.get(nic=nicid)
        contact_number = request.POST['contact']
        username = request.POST['username']
        pswrd = request.POST['password1']

        try:
            user = RegisteredUser.objects.create_user(nic=nic, username=username, password=pswrd, contact_number=contact_number)
            user.save()
        except:
            messages.error(request, "Username Exists")
            return redirect('confirm')

        profile = Profile(user=user)
        profile.save()
        auth.login(request, user)
        return redirect('otp')
            
    else:
        return render(request, 'confirm.html')


def send_otp(user):

    profile = Profile.objects.get(user=user)
    mobile = user.contact_number

    if cache.get(mobile):
        total_calls = cache.get(mobile)
        if total_calls>3:
            return False, cache.ttl(mobile)
        else:
            otp = str(random.randint(100000, 999999))
            profile.otp = otp
            profile.save()
            cache.set(mobile, total_calls+1)
            return True, 0

    otp = str(random.randint(100000, 999999))
    profile.otp = otp
    profile.save()
    cache.set(mobile, 1, timeout=60)
    return True, 0



def otp(request):
    
    user = request.user

    if request.method == 'POST':

        status, secs = throttle(request, 's')
        if status:
            messages.error(request, 'Maximum Rate Exceeded. Wait for '+str(secs)+'s')
            return redirect('otp', user)
        

        profile = Profile.objects.get(user=user)
        otp = request.POST['otp']
        if otp == profile.otp:
            profile.is_verified = True
            profile.save()
            request.session['username'] = user.username
            throttle(request, 'd')
            return redirect('home')

        else:
            messages.error(request, "Invalid OTP")
            return redirect('otp')

    else:

        status, secs = send_otp(user)
        digits = 'na'
        if not status:
            messages.error(request, 'Try again in '+str(secs)+'s')
        
        else:
            digits = user.contact_number[-2:]
       
        return render(request, 'otp.html', {'digits':digits})



def throttle(request, opt):

    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        ip = forwarded.split(',')[-1].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')

    if (opt=='s'):
        if cache.get(ip):
            total_calls = cache.get(ip)
            if total_calls>4:
                return True, cache.ttl(ip)
            else:
                cache.set(ip, total_calls+1)
                return False, 0
        
        cache.set(ip, 1, timeout=60)
        return False, 0

    elif (opt=='d'):
        if cache.get(ip):
            cache.delete(ip)
            return True, 0
        
    return False, 0



def resetpassword(request):

    if not request.user.is_authenticated:
        return redirect('login')



def rememberdevice(request):

    if not request.user.is_authenticated:
        return redirect('login')

    if request.method=='POST':

        agent = request.POST['agent']
        ip = request.POST['ip']
        # enter to database table 'sessions'

        randomstring = ''.join(random.choices(string.ascii_letters+string.digits, k=20))
        response = HttpResponse()
        response.set_signed_cookie('token', randomstring)
        return response


def forgetdevice(request):

    if not request.user.is_authenticated:
        return redirect('login')

    if request.method=='POST':

        response = HttpResponse()
        response.delete_cookie('token')
        # delete from the database
        return response



def home(request):

    if not request.user.is_authenticated:
        return redirect('login')

    result = calc(request,"call PERCENTAGE_CALC(%(nic)s)")
    traceDet = []
    for i in result:
        thisdict = {
        "shop": i[0],
        "location": i[1],
        "percent": float(i[2]),
        "temp": float(i[3]),
        "date": str(i[4]),
        "time": str(i[5])
        }
        traceDet.append(thisdict)
    json_string = json.dumps(traceDet)    
    
    return render(request, 'home.html', {'TraceLocation': json_string, 'user': request.user})



def trace(request):

    if not request.user.is_authenticated:
        return redirect('login')

    result = calc(request,"call PERCENTAGE_CALC(%(nic)s)")
    return render(request, 'trace.html',{'TraceLocation':result})


def logout(request):

    if not request.user.is_authenticated:
        return redirect('login')

    auth.logout(request)
    return redirect('login')


def myaccount(request):

    if not request.user.is_authenticated:
        return redirect('login')
    
    devs = DeviceSessions.objects.filter(user=request.user)
    for dev in devs:
        if dev.token is None:
            dev.token = '0'
        else:
            dev.token = '1'

    return render(request, 'myaccount.html', {'devices': devs})


def forgotpassword(request):

    if not request.user.is_authenticated:
        return redirect('login')
    


def search(request):

    if not request.user.is_authenticated:
        return redirect('login')

    result = calc(request,"call TOP_INFECTED_PLACES_IN_USER_AREA(%(nic)s)")
    return render(request, 'search.html',{'TopInfected':result})



def calc(request,query):

    if not request.user.is_authenticated:
        return redirect('login')

    user=request.user
    cursor = connection.cursor()
    cursor.execute(query,{ 'nic': user.nic.nic })
    result = cursor.fetchall()
    return (result)




'''def calc(request):

    if not request.user.is_authenticated:
        return redirect('login')

    user=request.user
    cursor = connection.cursor()
    cursor.execute("call PERCENTAGE_CALC(%(nic)s)",{ 'nic': user.nic.nic })
    result = cursor.fetchall()
    #result = dict_fetchall(cursor)
    return (result)
'''


def load_more(request):
    merchant= request.GET.get('merchant')
    area = request.GET.get('area')
    #print(type(merchant))
    result = infectPercent(str(merchant),str(area))
    #post_obj = result[1]
    data = {
        'posts': result
    }
    return JsonResponse(data=data)


def infectPercent(merchant,area):
    cursor = connection.cursor()
    cursor.execute("call SEARCH_INFECT_PERCENTAGE(%(merchant)s,%(area)s)",{ 'merchant': merchant, 'area': area})
    result = cursor.fetchall()
    #result = dict_fetchall(cursor)
    return (result)

