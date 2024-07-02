import sqlite3 as sql
from flask import Flask, render_template, url_for, request, session, flash, redirect
import sqlite3 as sql
import regex as re
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from werkzeug.exceptions import BadRequestKeyError

app = Flask(__name__)
app.secret_key = "mydietkey"

# read the dataset
df = pd.read_csv("healthy-recipes-csv.csv")

@app.errorhandler(BadRequestKeyError)
def handle_bad_request(e):
    # The user's session has expired
    message = 'Your session has expired. Please refresh the page to log in again.'
    return render_template('error.html', message=message), 400

def fav(food1):
    food1 = food1.reset_index()

    count1 = CountVectorizer(stop_words='english')
    count_matrix = count1.fit_transform(food1['Keywords'])

    cosine_sim2 = cosine_similarity(count_matrix, count_matrix)

    # Get the pairwise similarity scores
    sim = list(enumerate(cosine_sim2[0]))
    # Sort the food based on the similarity scores
    sim = sorted(sim, key=lambda x: x[1], reverse=True)
    # Get the scores of the 10 most similar food
    sim = sim[1:11]
    # Get the food indices
    indi = [i[0] for i in sim]

    final = food1.copy().iloc[indi[0]]
    final = pd.DataFrame(final)
    final = final.T

    for i in range(1, len(indi)):
        final1 = food1.copy().iloc[indi[i]]
        final1 = pd.DataFrame(final1)
        final1 = final1.T
        final = pd.concat([final, final1])
    return final

def rest_rec(ingredient=[],ingredientP=[],ingredientNVeg=[],fav_food="", df=df):
    #print(df['RecipeIngredientParts'].to_string())

    #For Vegetable Options
    #Select rows with RecipeIngredientParts contains specified string
    df_ing = df.copy().loc[df['RecipeIngredientParts'].str.contains(ingredient[0])]
    #print (df_ing)
    df_ing['Start'] = df_ing['RecipeIngredientParts'].str.find(ingredient[0])
    df_cui = df_ing.copy().loc[df_ing['Start'] >= 0]

    for i in range(1, len(ingredient)):
        df_ing['Start'] = df_ing['RecipeIngredientParts'].str.find(ingredient[i])
        df_cu = df_ing.copy().loc[df_ing['Start'] >= 0]
        df_cui = pd.concat([df_cui, df_cu])
        df_cui.drop_duplicates(subset='Name', keep='last', inplace=True)
    
    #For Seeds and Nuts Options
    #Save vegetable_ingredients to continue find and work with another seeds and nuts ingredient
    df_ingP = df_cui.copy()
    df_ingP['Start'] = df_ingP['RecipeIngredientParts'].str.find(ingredientP[0])
    df_cuiP = df_ingP.copy().loc[df_ingP['Start'] >= 0]

    for i in range(1, len(ingredientP)):
        df_ingP['Start'] = df_ingP['RecipeIngredientParts'].str.find(ingredientP[i])
        df_cuP = df_ingP.copy().loc[df_ingP['Start'] >= 0]
        df_cuiP = pd.concat([df_cuiP, df_cuP])
        df_cuiP.drop_duplicates(subset='Name', keep='last', inplace=True)

    #For Non Vegetable
    #Save nuts (ingredientP) to continue find and work with another non vegetable options
    df_ingNVeg = df_cuiP.copy()
    df_ingNVeg['Start'] = df_ingNVeg['RecipeCategory'].str.find(ingredientNVeg[0])
    df_cuiNV = df_ingNVeg.copy().loc[df_ingNVeg['Start'] >= 0]

    for i in range(1, len(ingredientNVeg)):
        df_ingNVeg['Start'] = df_ingNVeg['RecipeCategory'].str.find(ingredientNVeg[i])
        df_cunveg = df_ingNVeg.copy().loc[df_ingNVeg['Start'] >= 0]
        df_cuiNV = pd.concat([df_cuiNV, df_cunveg])
        df_cuiNV.drop_duplicates(subset='Name', keep='last', inplace=True)

    if fav_food != "":
        favr = df.loc[df['Name'] == fav_food].drop_duplicates()
        favr = pd.DataFrame(favr)
        food3 = pd.concat([favr, df_cuiNV])
        food3.drop('Start', axis=1, inplace=True)
        food_selected = fav(food3)
    else:
        df_cuiNV = df_cuiNV.sort_values('AggregatedRating', ascending=False)   #sort the rows according to rating value
        food_selected = df_cuiNV.head(20)   # get only 10 food name
    return food_selected

def calc(ingredient, ingredientP, ingredientNVeg):
    food_sugg = rest_rec([ingredient],[ingredientP],[ingredientNVeg])
    food_list1 = food_sugg.copy().loc[:,
                ['Name', 'Calories', 'ProteinContent', 'FatContent', 'SodiumContent', 'RecipeCategory', 'RecipeIngredientParts']]
    
    #session recall body goal from user information 
    get_goal = session.get("goal")
    print (get_goal)
    # Creates DataFrame
    food_list = pd.DataFrame(food_list1)

    # selecting rows based on condition 
    if get_goal == "gain":
        recommend_result = food_list.loc[(food_list['Calories'] >= 450)]
    elif get_goal == "loss":
        recommend_result = food_list.loc[(food_list['Calories'] <= 450)]
    else:
        recommend_result = food_list.loc[(food_list['Calories'] >= 0) & (food_list['Calories'] <= 900)]   
    print (recommend_result)

    food_list = recommend_result.reset_index()
    food_list = food_list.rename(columns={'index': 'RecipeId'})
    food_list.drop('RecipeId', axis=1, inplace=True)
    food_list = food_list.T
    food_list = food_list
    ans = food_list.to_dict()
    fL = [value for value in ans.values()]
    return fL 

# connect to database sqlite
def db_connect():
    conn = sql.connect(
        r"E:\BSC Hons (Hons 5) - Subjects\Hons Project\Diet recommender system using Collaborative Filtering technique\Diet recommender system\mydiet.db")
    conn.row_factory = sql.Row
    return conn

@app.route("/")
def index():
    conn = db_connect()
    user = conn.execute('SELECT * FROM user').fetchall()
    conn.close()
    return render_template('index.html', user=user)

# user login
@app.route("/userLogin", methods=["GET", "POST"])
def userLogin():
    if request.method == "GET":
        return render_template("user.html")
    else:
        # Create variables for better access
        emailAddr = request.form["email"]
        userPass = request.form["password"]

        # check if the account exist
        with db_connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user WHERE email=?", (emailAddr,))
            rows = cursor.fetchone()

            # If the account exist show message
            if rows is not None:
                account_pass = rows[3]
                # print(account_pass)
                # print (rows[0])
            # return uid to userInfo & email to choose,recommend route
                session["uid"] = rows[0]
                session["email"] = rows[2]
                if account_pass == userPass:
                    flash("User login pass!")
                    return render_template("user.html", emailAddr=emailAddr)

            # If the account not exist show message
                else:
                    flash("Invalid Access. Please Try Again!")
                    return redirect("/")
            else:
                flash("Invalid Account. Email or Password is Incorrect.")
                return redirect("/")

# user registration
@app.route("/userRegister", methods=["GET", "POST"])
def userRegister():
    if request.method == "GET":
        return render_template("index.html")  # need to login
    else:
        # Create variables for better access
        userName = request.form["uName"]
        emailAddr = request.form["email"]
        userPass = request.form["password"]
        rePass = request.form["password_confirm"]

        # check if the account exist, email pattern, two password match
        with db_connect() as connect:
            cursor = connect.cursor()
            cursor.execute("SELECT * FROM user WHERE email=?", (emailAddr,))
            account = cursor.fetchone()
            if account:
                flash("Account Already Exists!")
                return redirect("/")
            if not userName or not userPass or not emailAddr:
                flash("Please fill out the form !")
            else:
                if rePass == userPass:
                    print(rePass)
                    if re.match(r'[^@]+@[^@]+\.[^@]+', emailAddr):
                        cursor.execute(
                            "INSERT INTO user (uName,email,password) VALUES (?,?,?)", (userName, emailAddr, userPass))
                        connect.commit()
                        flash("Register Successful")
                        return redirect("/")
                    else:
                        flash("Enter your email addr correctly!")
                        return redirect("/")
                else:
                    flash("Enter password correctly!")
                    return redirect("/")

# user information
@app.route("/userInfo", methods=["GET", "POST"])
def userInfo():
    if request.method == "GET":
        return render_template("user.html")
    else:
        # Create variables for better access
        userAge = request.form["age"]
        userWeight = request.form["weight"]
        userHeight = request.form["height"]
        userGender = request.form["gender"]
        userGoal = request.form["goal"]
        userActivity = request.form["activity"]

        # recalled user id from login route
        get_uid = session.get("uid")
        # Calculate the BMI to determine the body situation
        output = int(userWeight)/(float(userHeight)/100)**2
        bmi = float(output)
        print(bmi)

        # Put the information into database
        with db_connect() as connect:
            cursor = connect.cursor()
            cursor.execute("INSERT INTO user_info (age,weight,height,gender,goal,activity,uid,bmi) VALUES (?,?,?,?,?,?,?,?)",
                           (userAge, userWeight, userHeight, userGender, userGoal, userActivity, get_uid, bmi))
            connect.commit()

            # return as session to recommend route to determine calorie intake
            session["age"] = userAge
            session["weight"] = userWeight
            session["height"] = userHeight
            session["gender"] = userGender
            session["goal"] = userGoal
            session["activity"] = userActivity

        # Give BMI Result
        if bmi <= 18.5:
            flash("You are Under weight as your bmi is:" + str(output))
            return redirect("/choose")
        elif (bmi >= 18.5) and (bmi <= 24.9):
            flash("Perfect! You have normal weight and your bmi is:" + str(output))
            return redirect("/choose")
        elif (bmi >= 25) and (bmi <= 29.9):
            flash("You are Overweight as your bmi is:" + str(output))
            return redirect("/choose")
        elif bmi >= 30:
            flash("You are highly obese as your bmi is:" + str(output))
            return redirect("/choose")
        else:
            flash("Healthy Weight. Your bmi is:" + str(output))
            return redirect("/choose")

# user choose
# @app.route("/choose")
# def choose():
#     # recalled user id from login route
#     get_email = session.get("email")
#     print(get_email)

#     # calling nuts from above
#     nutlist = nuts
#     print (nutlist)
#     non_veglist = non_vegs
#     print (non_veglist)

#     return render_template('choose.html', get_email=get_email, nut=nutlist, non_veg=non_veglist)

# user recommendation
@app.route("/choose", methods=["GET", "POST"])
def choose():
    if request.method == "GET":
        return render_template("choose.html")
    else:
        ingredient1 = request.form['ingredient']
        ingredient2 = request.form['ingredientP']
        ingredient3 = request.form['ingredientNVeg']
        fL = calc(ingredient1, ingredient2, ingredient3)
        print (fL)

        # selecting rows based on condition 
        #rslt_df = dframe.loc[dframe['Calories'] > 400]    
        
        # recalled user id from login route
        get_email = session.get("email")
        print(get_email)
        get_age = session.get("age")
        get_weight = session.get("weight")
        get_height = session.get("height")
        get_gender = session.get("gender")
        get_activity = session.get("activity")

        # BMR calculate to determine the amount of energy (form of calorie) body need
        # weight in kg and height in cm
        maleBMR = 66.5 + (13.75 * int(get_weight)) + \
            (5.003 * int(get_height)) - (6.75 * int(get_age))
        femaleBMR = 655.1 + (9.563 * int(get_weight)) + \
            (1.850 * int(get_weight)) - (4.676 * int(get_age))

        if get_gender == "male" and get_activity == "sedentary":
            # the Harris-Benedict equation to determine total daily calorie needs
            calorie = maleBMR * 1.25
        elif get_gender == "male" and get_activity == "lightActive":
            calorie = maleBMR * 1.375
        elif get_gender == "male" and get_activity == "moderateActive":
            calorie = maleBMR * 1.550
        elif get_gender == "male" and get_activity == "veryActive":
            calorie = maleBMR * 1.725
        else:
            if get_gender == "female" and get_activity == "sedentary":
                calorie = femaleBMR * 1.25
            elif get_gender == "male" and get_activity == "lightActive":
                calorie = femaleBMR * 1.375
            elif get_gender == "male" and get_activity == "moderateActive":
                calorie = femaleBMR * 1.550
            else:
                calorie = femaleBMR * 1.725

        calorie = int(calorie)
        return render_template('recommend.html', get_email=get_email, calorie=calorie, food = fL)
        
@app.route('/logout')
def logout():
    session.pop('email',None)
    return redirect(url_for('index'))


if __name__ == "__main__":
    app.run(debug=True, port=5561)

