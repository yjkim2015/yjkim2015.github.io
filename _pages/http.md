---
title: "Http"
layout: default
permalink: /categories/http/
---

<div class="main-container">
  <div class="content-container">
    <h1 class="category-page__title">Http</h1>

    {% assign posts = site.categories["Http"] %}
    {% for post in posts %}
      {% include archive-single.html %}
    {% endfor %}
  </div>
</div>
