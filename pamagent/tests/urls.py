from django.conf.urls import url
from django.http import HttpResponse
import requests


def index(_):
    requests.get("http://ya.ru")
    return HttpResponse("You're looking at index %s")


urlpatterns = [url("^$", index)]
