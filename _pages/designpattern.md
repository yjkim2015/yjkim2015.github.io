---
title: "DesignPattern"
layout: default
permalink: /categories/designpattern/
---

<div class="main-container">
  <div class="content-container">
    <h1 class="category-page__title">DesignPattern</h1>

    <div class="posts-grid">
      {% assign posts = site.categories["DesignPattern"] %}
      {% for post in posts %}
        {% include archive-single.html type="card" %}
      {% endfor %}
    </div>
  </div>
</div>
