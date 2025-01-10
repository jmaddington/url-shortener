import os
import tempfile
import subprocess
from flask import Flask, request, redirect, render_template_string, send_file, abort, session, url_for, make_response
from werkzeug.utils import secure_filename
from flask_session import Session
from urllib.parse import urlparse
import logging
import shutil

from auth import requires_auth, init_saml_auth, prepare_flask_request
from database import init_db, get_db, close_db, record_click, get_link_stats
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)
Session(app)

# Initialize database
with app.app_context():
    init_db()

# Admin panel HTML template
ADMIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>URL Shortener Admin</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', sans-serif;
        }

        body {
            background-color: #f5f5f5;
            color: #333;
            line-height: 1.6;
            padding: 2rem;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        h1 {
            color: #2d3748;
            font-size: 2.5rem;
            margin-bottom: 2rem;
            text-align: center;
        }

        h2 {
            color: #4a5568;
            font-size: 1.5rem;
            margin: 2rem 0 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #e2e8f0;
        }

        .card {
            background: white;
            border-radius: 10px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .form-group {
            margin-bottom: 1.5rem;
        }

        label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
            color: #4a5568;
        }

        input[type="text"],
        input[type="url"],
        textarea {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            font-size: 1rem;
            font-family: inherit;
            transition: border-color 0.2s;
            resize: vertical;
        }

        textarea:focus {
            outline: none;
            border-color: #4299e1;
            box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.2);
        }


        input[type="file"] {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            font-size: 1rem;
            transition: border-color 0.2s;
        }

        input[type="text"]:focus,
        input[type="url"]:focus {
            outline: none;
            border-color: #4299e1;
            box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.2);
        }

        button {
            background-color: #4299e1;
            color: white;
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 6px;
            font-weight: 500;
            cursor: pointer;
            transition: background-color 0.2s;
        }

        button:hover {
            background-color: #3182ce;
        }

        button.delete {
            background-color: #e53e3e;
        }

        button.delete:hover {
            background-color: #c53030;
        }

        button.copy {
            background-color: #48bb78;
            padding: 0.5rem 1rem;
            margin-left: 0.5rem;
        }

        button.copy:hover {
            background-color: #38a169;
        }

        button.copy.copied {
            background-color: #68d391;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        th, td {
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }

        th {
            background-color: #f7fafc;
            font-weight: 600;
            color: #4a5568;
        }

        tr:hover {
            background-color: #f7fafc;
        }

        .badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.875rem;
            font-weight: 500;
        }

        .badge.url {
            background-color: #ebf4ff;
            color: #4299e1;
        }

        .badge.file {
            background-color: #f0fff4;
            color: #48bb78;
        }

        .user-info {
            text-align: right;
            margin-bottom: 1rem;
            color: #4a5568;
        }

        .user-info .user-name {
            font-weight: 500;
            color: #2d3748;
        }

        .logout-btn {
            background-color: #718096;
            font-size: 0.875rem;
            padding: 0.5rem 1rem;
            margin-left: 0.5rem;
        }

        .logout-btn:hover {
            background-color: #4a5568;
        }

        .download-btn {
            background-color: #6B7280;
            font-size: 0.875rem;
            padding: 0.5rem 1rem;
            margin-left: 0.5rem;
            text-decoration: none;
            color: white;
            border-radius: 6px;
            display: inline-block;
        }

        .download-btn:hover {
            background-color: #4B5563;
        }

        .download-btn i {
            margin-right: 0.5rem;
        }

        .copy-tooltip {
            position: fixed;
            background: #1a202c;
            color: white;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 14px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
        }

        .stats-link {
            color: #4299e1;
            text-decoration: none;
            margin-left: 1rem;
        }

        .stats-link:hover {
            text-decoration: underline;
        }

        @media (max-width: 768px) {
            body {
                padding: 1rem;
            }

            .card {
                padding: 1rem;
            }

            table {
                display: block;
                overflow-x: auto;
                white-space: nowrap;
            }

            th, td {
                padding: 0.75rem;
            }
        }

        .forms-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin-bottom: 2rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="user-info">
            {% if user %}
                Logged in as <span class="user-name">{{ user.name }}</span>
                <a href="/download-repo" class="download-btn">
                    <i class="fas fa-download"></i> Download Repository
                </a>
                <a href="/sso/logout" class="button logout-btn">Logout</a>
            {% endif %}
        </div>

        <h1>URL Shortener Admin</h1>
        
        <div class="forms-container">
            <div class="card">
                <h2>Create URL Redirect</h2>
                <form method="POST" action="/admin/create">
