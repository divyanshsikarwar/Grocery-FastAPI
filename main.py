from fastapi import FastAPI
from datetime import datetime
from typing import Optional
import sqlite3
conn = sqlite3.connect('grocery.db', check_same_thread=False) #connect to database
c = conn.cursor() 

tags_metadata = [
    {
        "name": "User Basic Operations",
        "description": "Basic operations like **Register**, **Login** and **Logout** can be performed by the user using these end points.",
    },
    {
        "name": "User Advanced Operations",
        "description": "operations like **Fething Menu**, **Adding Items to Cart** and **Placing Order** can be performed by the user using these end points.",
    },
    {
        "name": "Store Manager Operations",
        "description": "Operations like **Adding Items**, **Deleting Items**, **Viewing Orders** can be performed by the store manager using these end points.",
        
    },
] #Description of Api Categories.

c.executescript("""
            CREATE TABLE IF NOT EXISTS store (userName text, email text, password text, address text, cart text,
            orders text, phoneNumber text); 
            CREATE TABLE IF NOT EXISTS loginSession (email text, password text, time text, sessionID text);
            CREATE TABLE IF NOT EXISTS menuDetails (itemName text, itemPrice integer, itemDescription text)""") 
# store table contains all the details of the user
# loginSession table contains sessionId and last logged in time of the user
# menuDetails table contains all the details of the items in the grocery store


def check_login_status(sessionID): #check_login_status checks if user is logged in or not
    c.execute("SELECT * FROM loginSession WHERE sessionID=?", (sessionID,))
    data = c.fetchall()
    if data is None:
        return False
    else:
        return data[1] #returns the corresponding email of the user


app = FastAPI(title= "Finbox Backend Task" ,openapi_tags=tags_metadata) 

@app.post("/new-registeration" , tags=["User Basic Operations"])
def new_registeration(email: str, password: str, address: str, phone: str, userName: Optional[str]=None):

    c.execute("INSERT INTO store VALUES (?,?,?,?,?,?,?)", (userName, email, password, address, "", "", phone))
    c.execute("INSERT INTO loginSession VALUES (?,?,?,?)", (email, password, "", ""))
    conn.commit()
    return {"message": "New User registered"}


@app.post("/login" , tags=["User Basic Operations"])
def login(email: str, password: str):
    status = login_status(email, password) #check if user is already logged in
    if("SessionToken" in status):
        c.execute("UPDATE loginSession SET time=? WHERE email=? AND password=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), email, password))
        return status
    
    c.execute("SELECT * FROM store WHERE email=? AND password=?", (email, password))
    resonse = None
    data = c.fetchone()
    
    sessionID = str(hash(email + str(datetime.now())))[0:4] 
    #generates a random sessionID which will be stored on the client side, SessionID will be used as a token to identify a user at the backend.
    if data:
        response =  {"message": "Login successful, welcome to the store", "SessionToken": sessionID}
    else:
        response = {"message": "Login failed, Email or Password entered is incorrect"}

    c.execute("UPDATE loginSession SET time=?, sessionID=? WHERE email=? AND password=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), sessionID, email, password))    
    conn.commit()
    return response
    

@app.get("/login-status" , tags=["User Basic Operations"])
def login_status(email: str, password: str, sessionID: Optional[str]=None):
    c.execute("SELECT * FROM loginSession WHERE email=? AND password=?", (email, password))
    data = c.fetchone()
    if(data is None or data[3]==""):
        return {"message": "You are not logged in, Use the login endpoint to login"}
    
    storedTime = datetime.strptime(data[2] ,"%Y-%m-%d %H:%M:%S")
    currTime = datetime.now()
    tdelta = currTime - storedTime
    if (tdelta.days==0 and tdelta.seconds/3600 <6): #check if current time is less than 6 hours from the last time user logged in.
        return {"message": "Already logged in",
                "SessionToken": data[3]}
    else:
        return {"message": "You are not logged in, Use the login endpoint to login"}

    
@app.get("/logout" , tags=["User Basic Operations"])
def logout(sessionID: str):
    c.execute("UPDATE loginSession SET time=?, sessionID=? WHERE email=? AND password=?", ("","", email, password))    
    conn.commit()
    return {"message": "Logout successful"}


@app.delete("/delete-user" , tags=["User Basic Operations"])
def delete_user(email: str, password: str):
    c.execute("DELETE FROM store WHERE email=? AND password=?", (email, password))
    c.execute("DELETE FROM loginSession WHERE email=? AND password=?", (email, password))
    conn.commit()
    return {"message": "User deleted"}


@app.get("/menu-items" , tags=["User Advanced Operations"])
def menu_items(sessionID: str):
    check = check_login_status(sessionID)
    if(check):
        c.execute("SELECT * FROM menuDetails")
        data = c.fetchall()
        return {"message": "Menu items", "menu": data}
    else:
        return {"message": "You need to login first to get menu items."}


@app.put("/add-item-to-cart" , tags=["User Advanced Operations"])
def add_item_to_cart(sessionID: str, itemName: str):
    c.execute("SELECT * FROM menuDetails WHERE itemName=?", (itemName,)) #check if item is in menu
    if(c.fetchone() == None):
        return {"message": "Item not found in the menu."}
    
    email = check_login_status(sessionID)
    if(email):
        c.execute("SELECT cart FROM store WHERE email=?", (email,))
        cart = c.fetchone()
        if(cart[0]==""):
            c.execute("UPDATE store SET cart=? WHERE email=?", (itemName, email))
        else:
            c.execute("UPDATE store SET cart=? WHERE email=?", (cart[0] + "," + itemName, email)) 
            #Items in the cart are stored as a string and are separated by commas
        conn.commit()
        return {"message": "Item added to cart"}
    else:
        return {"message": "You need to login first to add items to cart"}


@app.delete("/remove-item-from-cart" , tags=["User Advanced Operations"])
def remove_item_from_cart(sessionID: str, itemName: str):
    email = check_login_status(sessionID)
    if(email):
        c.execute("SELECT cart FROM store WHERE email=?", (email,))
        cart = c.fetchone()
        if(cart[0]==""):
            return {"message": "Cart is empty"}
        else:
            c.execute("UPDATE store SET cart=? WHERE email=?", (cart[0].replace(itemName, ""), email)) #replace the item with empty string
        conn.commit()
        return {"message": "Item removed from cart"}
    else:
        return {"message": "You need to login first to remove items from cart"}


@app.post("/place-order" , tags=["User Advanced Operations"])
def place_order(sessionID: str):
    email = check_login_status(sessionID)
    if(email):
        c.execute("SELECT cart FROM store WHERE email=?", (email,))
        cart = c.fetchone()
        if(cart[0]==""):
            return {"message": "Cart is empty"}
        else:
            c.execute("UPDATE store SET orders=? WHERE email=?", (cart[0], email)) #add the items in the cart to the orders.
            c.execute("UPDATE store SET cart=? WHERE email=?", ("", email)) #removes all of the cart items.
        conn.commit()
        return {"message": "Order placed"}
    else:
        return {"message": "You need to login first to place order"}


@app.post("/add-menu-item" , tags=["Store Manager Operations"])
def add_menu_item(itemName: str, itemPrice: str, itemDescription: str):
        c.execute("INSERT INTO menuDetails VALUES (?,?,?)", (itemName, itemPrice, itemDescription))
        conn.commit()
        return {"message": "Item added to menu"}


@app.delete("/delete-menu-item" , tags=["Store Manager Operations"])
def delete_menu_item(itemName: str):
        c.execute("DELETE FROM menuDetails WHERE itemName=?", (itemName,))
        conn.commit()
        return {"message": "Item deleted from menu"}


@app.get("/view-orders" , tags=["Store Manager Operations"])
def view_orders():
    c.execute("SELECT orders FROM store")
    data = c.fetchall()
    return {"message": "Orders", "orders": data}

if __name__ == "__main__":
    uvicorn.run("app.api:app", host="0.0.0.0", port=8080, reload=True)
    
# => uvicorn main:app --reload
