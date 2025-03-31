#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os

class DefaultConfig:
    """ Bot Configuration """

    PORT = 8000
    APP_ID = os.environ["MicrosoftAppId"]
    APP_PASSWORD = os.environ["MicrosoftAppPassword"]
    
    if not APP_ID:
        print(" MicrosoftAppId is not set!")
    if not APP_PASSWORD:
        print(" MicrosoftAppPassword is not set!")
