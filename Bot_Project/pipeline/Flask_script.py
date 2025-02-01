#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from flask import Flask, request, jsonify
from Route_Perfect_pipe import pipeline_flow


# In[ ]:


app = Fask(__name__)


# In[ ]:


@app.route("/process", methods=["POST"]) # a decorator with url activating the function and the method related to receiving data

def process():
    data = request.json
    input_data = data.get('message', '')

    result = pipeline_flow(input_data)

    return jsonify({'result': result})


if name == "__main__":
    app.run(host="0.0.0.0", port=5000)

