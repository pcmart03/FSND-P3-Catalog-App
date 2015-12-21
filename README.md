#Udacity FSND Project 3 Catalog App

This is an application for creating and maintaining an item catalog. Users can log in with either Google+ or Facebook to log into the app and create new items.  

A working demo of the app is [available here](http://ec2-52-26-24-122.us-west-2.compute.amazonaws.com/).

##Running the App

###Prerequisites
- Python
- Flask v0.9
- Sqlalchemy
- Sqlite or Postgresql

###To Install
Clone or download the repository and cd into the directory.

cd into the directory and enter `python catalog.py`

Open a browser and navigate to http://localhost:8000

##Using the App

You can browse existing items without logging in. However, you will need to log in to perform admin actions.

##Managing Photos

Photos are managed seperately from items to allow for image reuse. 

###Add a photo
Click `Manage Photos > Add photo`

On the next screen, select a photo to upload, enter a alternate text and a category for the photo.

###Delete a Photo
Click `Manage Photos > Delete photo`

You can only delete photos you have uploaded and that are not currently being used by any items.

Select the photo you would like to delete and click "Delete"

##Managaing Items

##Adding Item
Navigate to the category you would like to ad an item to and click "Add item"

Fill out the information on the next page and select a photo. Then click "Create"

##Editing Item
Note: You can only Edit items that you created

Navigate to the item you wish to edit and click "Edit"
Make the desired changes and click "Save"

##Deleting Items
Navigate to the item you wish to edit and click "Delete"
Confirm you want to delete the item

API endpoints
Categories: http://localhost:8000/category/JSON
Items in Category: http://localhost:8000/category/<category_id>/JSON
Item: http://localhost:8000/item/<int:item_id>/JSON
