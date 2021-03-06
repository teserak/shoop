# -*- coding: utf-8 -*-
# This file is part of Shoop.
#
# Copyright (c) 2012-2016, Shoop Ltd. All rights reserved.
#
# This source code is licensed under the AGPLv3 license found in the
# LICENSE file in the root directory of this source tree.
from jinja2.utils import contextfunction

from shoop.core.models import (
    AttributeVisibility, Product, ProductAttribute, ProductCrossSell,
    ProductCrossSellType, Supplier
)
from shoop.utils.text import force_ascii


def get_visible_attributes(product):
    return ProductAttribute.objects.filter(
        product=product,
        attribute__visibility_mode=AttributeVisibility.SHOW_ON_PRODUCT_PAGE
    )


# Deprecated, see `get_product_cross_sells()`
@contextfunction
def get_products_bought_with(context, product, count=5):
    related_product_cross_sells = (
        ProductCrossSell.objects
        .filter(product1=product, type=ProductCrossSellType.COMPUTED)
        .order_by("-weight")[:(count * 4)])
    products = []
    for cross_sell in related_product_cross_sells:
        product2 = cross_sell.product2
        if product2.is_visible_to_user(context["request"].user) and product2.is_list_visible():
            products.append(product2)
        if len(products) >= count:
            break
    return products


@contextfunction
def is_visible(context, product):
    request = context["request"]
    shop_product = product.get_shop_instance(shop=request.shop)
    for error in shop_product.get_visibility_errors(customer=request.customer):  # pragma: no branch
        return False
    return True


@contextfunction
def get_product_cross_sells(
        context, product, relation_type=ProductCrossSellType.RELATED,
        count=4, orderable_only=True):
    request = context["request"]
    rtype = map_relation_type(relation_type)
    related_product_ids = list((
        ProductCrossSell.objects
        .filter(product1=product, type=rtype)
        .order_by("weight")[:(count * 4)]).values_list("product2_id", flat=True)
    )

    related_products = []
    for product in Product.objects.filter(id__in=related_product_ids):
        shop_product = product.get_shop_instance(request.shop)
        if orderable_only:
            for supplier in Supplier.objects.all():
                if shop_product.is_orderable(supplier, request.customer, shop_product.minimum_purchase_quantity):
                    related_products.append(product)
                    break
        elif shop_product.is_visible(request.customer):
            related_products.append(product)

    # Order related products by weight. Related product ids is in weight order.
    # If same related product is linked twice to product then lowest weight stands.
    related_products.sort(key=lambda prod: list(related_product_ids).index(prod.id))

    return related_products[:count]


def map_relation_type(relation_type):
    """
    Map relation type to enum value.

    :type relation_type: ProductCrossSellType|str
    :rtype: ProductCrossSellType
    :raises: `LookupError` if unknown string is given
    """
    if isinstance(relation_type, ProductCrossSellType):
        return relation_type
    attr_name = force_ascii(relation_type).upper()
    try:
        return getattr(ProductCrossSellType, attr_name)
    except AttributeError:
        raise LookupError('Unknown ProductCrossSellType %r' % (relation_type,))
