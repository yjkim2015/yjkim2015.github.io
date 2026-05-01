---
title: "KAFKA"
layout: default
permalink: /categories/kafka/
---

<div class="main-container">
  <div class="content-container">
    <h1 class="category-page__title">KAFKA</h1>

    {% assign posts = site.categories["KAFKA"] %}
    {% for post in posts %}
      {% include archive-single.html %}
    {% endfor %}
  </div>
</div>
