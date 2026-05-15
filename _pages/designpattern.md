---
title: "DesignPattern"
layout: default
permalink: /categories/designpattern/
---

<div class="content-container" style="max-width:1100px; margin:0 auto; padding:2em 1em;">
  <h1 class="category-page__title">DesignPattern</h1>

  <div class="posts-grid">
    {% assign posts = site.categories["DESIGNPATTERN"] %}
    {% for post in posts %}
      {% include archive-single.html type="card" %}
    {% endfor %}
  </div>
</div>
