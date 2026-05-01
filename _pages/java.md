---
title: "JAVA"
layout: default
permalink: /categories/java/
---

<div class="main-container">
  <div class="content-container">
    <h1 class="category-page__title">JAVA</h1>

    {% assign posts = site.categories["JAVA"] %}
    {% for post in posts %}
      {% include archive-single.html %}
    {% endfor %}
  </div>
</div>
