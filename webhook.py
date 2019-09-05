from flask import Flask, redirect, url_for,request  

app = Flask(__name__)

@app.route('/success/<name>')
def success(name):
   return 'welcome %s' % name
   
if __name__ == '__main__':
   app.run()   
   
