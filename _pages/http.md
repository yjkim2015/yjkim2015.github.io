---
title: "Http"
layout: default
permalink: /categories/http/
---

<div class="content-container" style="max-width:1100px; margin:0 auto; padding:2em 1em;">
  <h1 class="category-page__title">Http</h1>

  <div class="posts-grid">
    {% assign posts = site.categories["HTTP"] %}
    {% for post in posts %}
      {% include archive-single.html type="card" %}
    {% endfor %}
  </div>
</div>
