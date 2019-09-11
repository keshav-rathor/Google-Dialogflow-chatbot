from flask import Flask
from flask import request, make_response
import os
import json
from pymongo import MongoClient
from bson.objectid import ObjectId
import traceback

MONGODB_URI = "mongodb+srv://kamlesh:techmatters123@aflatoun-quiz-pflgi.mongodb.net/test?retryWrites=true&w=majority"
client = MongoClient(MONGODB_URI, connectTimeoutMS=30000)
db = client.aflatoun
questions = db.questions

# Empty list for previously asked question
previous_questions = []

# Flask app should start in global layout
app = Flask(__name__)


# Defining a function which inputs a text and outputs the formatted object to return in facebook response
def make_text_response(message, platform="FACEBOOK"):
    return {
        "text": {
            "text": [
                message
            ]
        },
        "platform": platform
    }


@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)
    res = process_request(req)
    res = json.dumps(res, indent=4)
    # print(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r


def process_request(req):
    try:
        action = req.get("queryResult").get("action")

        if action == "input.welcome":
            # CLear the previous question list if start over
            previous_questions.clear()
            return {
                "source": "webhook"
            }

        elif action == "ask.question":
            result = req.get("queryResult")
            category = result.get("parameters").get("category")
            question = questions.find_one({"category": category,
                                           "type": "multiple_choice",
                                           "_id": {"$nin": previous_questions}})
            if not question:
                return {
                    "source": "webhook",
                    "fulfillmentMessages": [
                        {
                            "text": {
                                "text": [
                                    "Congratulations. You have completed the Quiz."
                                    "\n\nSuggestedReplies:\n4 - Continue with " + category + "\n1 - See other topics"
                                    # TODO: Option number should be dynamic
                                ]
                            }
                        },
                        {
                            "quickReplies": {
                                "title": "Congratulations. You have completed the Quiz.",
                                "quickReplies": [
                                    "Continue with " + category,
                                    "See Other Topic"
                                ]
                            },
                            "platform": "FACEBOOK"
                        }
                    ],
                    "outputContexts": [
                        {
                            "name": "projects/aflatoun-gmncrs/agent/sessions/b4bf3dcb-92ff-450c-aac2-566c4a92bbd5"
                                    "/contexts/ask_survey",
                            "lifespanCount": 1,
                            "parameters": {
                                "category": category,
                            }
                        }
                    ]
                }
            return {
                "source": "webhook",
                "fulfillmentMessages": [
                    {
                        "text": {
                            "text": [
                                question.get("question") + "\n\nYour options are:\n" + "\n".join(question.get("option"))
                            ]
                        }
                    },
                    {
                        "text": {
                            "text": [
                                question.get("question")
                            ]
                        },
                        "platform": "FACEBOOK"
                    },
                    {
                        "quickReplies": {
                            "title": "\n".join(question.get("option")),
                            "quickReplies": "A,B,C,D,E".split(",")[:len(question.get("option"))]
                        },
                        "platform": "FACEBOOK"
                    }
                ],
                "outputContexts": [
                    {
                        "name": "projects/aflatoun-gmncrs/agent/sessions/b4bf3dcb-92ff-450c-aac2-566c4a92bbd5"
                                "/contexts/check_answer",
                        "lifespanCount": 1,
                        "parameters": {
                            "category": category,
                            "question_id": str(question.get("_id"))
                        }
                    }
                ]
            }

        elif action == "check.answer":
            result = req.get("queryResult")
            category = result.get("parameters").get("category")
            selected_option = result.get("parameters").get("selected_option")
            question_id = ObjectId(result.get("parameters").get("question_id"))
            question = questions.find_one({"_id": question_id})

            if selected_option in question.get("answer"):
                # Adding the question_id to previous_question list so that next time it these questions are filtered
                # out.
                previous_questions.append(question_id)
                speech = "Well done, that is the correct answer."
                return {
                    "source": "webhook",
                    "fulfillmentMessages": [
                        {
                            "text": {
                                "text": [
                                    speech + "\n\nSuggested Replies:\n8 - Take Another Quiz\n1 - See Other Topic"
                                ]
                            }
                        },
                        {
                            "quickReplies": {
                                "title": speech,
                                "quickReplies": [
                                    "Take Another Quiz",
                                    "See Other Topic"
                                ]
                            },
                            "platform": "FACEBOOK"
                        }
                    ],
                    "outputContexts": [
                        {
                            "name": "projects/aflatoun-gmncrs/agent/sessions/b4bf3dcb-92ff-450c-aac2-566c4a92bbd5"
                                    "/contexts/AskQuestion",
                            "lifespanCount": 1,
                            "parameters": {
                                "category": category,
                            }
                        }
                    ]
                }
            else:
                speech = "Wrong answer, but nice attempt."
                return {
                    "source": "webhook",
                    "fulfillmentMessages": [
                        {
                            "text": {
                                "text": [
                                    speech + "\n\nSuggested Replies:\n8 - Try Again\n1 - See Other Topic"
                                ]
                            }
                        },
                        {
                            "quickReplies": {
                                "title": speech,
                                "quickReplies": [
                                    "Try Again",
                                    "See Other Topic"
                                ]
                            },
                            "platform": "FACEBOOK"
                        }
                    ],
                    "outputContexts": [
                        {
                            "name": "projects/aflatoun-gmncrs/agent/sessions/b4bf3dcb-92ff-450c-aac2-566c4a92bbd5"
                                    "/contexts/AskQuestion",
                            "lifespanCount": 1,
                            "parameters": {
                                "category": category,
                            }
                        }
                    ]
                }

        elif action == "check.answer-user.dont.know":
            result = req.get("queryResult")
            question_id = ObjectId(result.get("parameters").get("question_id"))
            category = result.get("parameters").get("category")
            question = questions.find_one({"_id": question_id})
            correct_answer_idx = question.get("answer_idx")
            option_list = question.get("option")
            previous_questions.append(question_id)
            return {
                "source": "webhook",
                "fulfillmentMessages": [
                    {
                        "quickReplies": {
                            "title": "The correct answer is: \n" +
                                     "\nOR\n".join([option_list[i] for i in correct_answer_idx]),
                            "quickReplies": [
                                "Take Another Quiz",
                                "See Other Topic"
                            ]
                        },
                        "platform": "FACEBOOK"
                    }
                ],
                "outputContexts": [
                    {
                        "name": "projects/aflatoun-gmncrs/agent/sessions/b4bf3dcb-92ff-450c-aac2-566c4a92bbd5"
                                "/contexts/AskQuestion",
                        "lifespanCount": 1,
                        "parameters": {
                            "category": category,
                        }
                    }
                ]
            }

        elif action == "ask-survey":
            result = req.get("queryResult")
            category = result.get("parameters").get("category")
            question = questions.find_one({"category": category, "type": "survey"})
            return {
                "source": "webhook",
                "fulfillmentMessages": [
                    {
                        "text": {
                            "text": [
                                "Watch this video to answer next questions."
                                "\nVideo Link: https://www.facebook.com/aflatoun/videos/242814000002095/\n\n" +
                                question.get("question") + "\n\n Start the Quiz? (Yes/No)"
                            ]
                        }
                    },
                    make_text_response("Watch this video to answer next questions."),
                    {
                        "payload": {
                            "facebook": {
                                "attachment": {
                                    "type": "template",
                                    "payload": {
                                        "template_type": "media",
                                        "elements": [
                                            {
                                                "media_type": "video",
                                                "url": "https://www.facebook.com/aflatoun/videos/242814000002095/",
                                                "buttons": [
                                                    {
                                                        "type": "web_url",
                                                        "url": "https://www.facebook.com/aflatoun/videos"
                                                               "/242814000002095/",
                                                        "title": "Watch"
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                }
                            }
                        },
                        "platform": "FACEBOOK"
                    },
                    make_text_response(question.get("question")),
                    {
                        "quickReplies": {
                            "title": "Start Quiz",
                            "quickReplies": [
                                "Yes",
                                "No"
                            ]
                        },
                        "platform": "FACEBOOK"
                    }
                ],
                "outputContexts": [
                    {
                        "name": "projects/aflatoun-gmncrs/agent/sessions/b4bf3dcb-92ff-450c-aac2-566c4a92bbd5"
                                "/contexts/AskQuestion-Survey-followup",
                        "lifespanCount": 1,
                        "parameters": {
                            "category": category,
                            "question_id": str(question.get("_id")),
                            "survey_count_flag": 0
                        }
                    }
                ]
            }

        elif action == "give.survey.option":
            result = req.get("queryResult")
            category = result.get("parameters").get("category")
            question_id = ObjectId(result.get("parameters").get("question_id"))
            question = questions.find_one({"_id": question_id})
            survey_count_flag = int(result.get("parameters").get("survey_count_flag"))
            if survey_count_flag <= len(question.get("surveys")):
                return {
                    "source": "webhook",
                    "fulfillmentMessages": [
                        {
                            "text": {
                                "text": [
                                    question.get("surveys")[survey_count_flag] + "\n" + "/".join(question.get("answer"))
                                ]
                            }
                        },
                        {
                            "quickReplies": {
                                "title": question.get("surveys")[survey_count_flag],
                                "quickReplies": question.get("answer")
                            },
                            "platform": "FACEBOOK"
                        }
                    ],
                    "outputContexts": [
                        {
                            "name": "projects/aflatoun-gmncrs/agent/sessions/b4bf3dcb-92ff-450c-aac2-566c4a92bbd5"
                                    "/contexts/AskQuestion-Survey-followup",
                            "lifespanCount": 1,
                            "parameters": {
                                "category": category,
                                "question_id": str(question.get("_id")),
                                "survey_count_flag": survey_count_flag + 1
                            }
                        }
                    ]
                }
            else:
                return {
                    "source": "webhook",
                    "fulfillmentMessages": [
                        {
                            "quickReplies": {
                                "title": "Thanks for completing the quiz.",
                                "quickReplies": [
                                    "Other topics"
                                ]
                            },
                            "platform": "FACEBOOK"
                        }
                    ]
                }

        elif action == "create.savings.plan":
            result = req.get("queryResult")
            income = result.get("parameters").get("Income")
            transportation = result.get("parameters").get("Transportation")
            food = result.get("parameters").get("Food")
            rent = result.get("parameters").get("Rent")
            miscellaneous = result.get("parameters").get("Miscellaneous")
            if income > (transportation + food + rent + miscellaneous):
                return {
                    "source": "webhook",
                    "fulfillmentMessages": [
                        make_text_response("You can save ${0} for this period. It is important to be disciplined "
                                           "in your savings. Remember to make adjustments from time to time and "
                                           "always remember to make room for new important expenses.".format(
                                income - (transportation + food + rent + miscellaneous)))
                    ]
                }
            elif income > (transportation + food + rent):
                return {
                    "source": "webhook",
                    "fulfillmentMessages": [
                        make_text_response("You are spending ${0} more in this period. It is important to be "
                                           "disciplined in your savings. Remember to make adjustments from time "
                                           "to time and always remember to make room for new important "
                                           "expenses.".format(income - (transportation + food + rent +
                                                                        miscellaneous)))
                    ]
                }

    except Exception as e:
        print("Error:", e)
        traceback.print_exc()
        return {
            "fulfillmentText": "Oops...I am not able to help you at the moment, please try again..",
            "source": "webhook"
        }


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print("Starting app on port {}".format(port))
    app.run(debug=False, port=port, host='0.0.0.0')
