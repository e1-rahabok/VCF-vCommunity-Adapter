#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging
from pyVmomi import vmodl, vim

logger = logging.getLogger(__name__)


def retrieve_properties(content, objectType, propertyPaths):
    """The objects of one type with the properties asked for, read from vCenter in pages.

    Raises when the read fails. An empty list means that vCenter has no such objects, so a failed read must not return
    one: the caller would publish "no VMs" for a read that did not happen.
    """
    view = None
    try:
        pc = content.propertyCollector

        view = content.viewManager.CreateContainerView(
            content.rootFolder,
            [objectType],
            True
        )

        traversal = vmodl.query.PropertyCollector.TraversalSpec(
            name='traverseEntities',
            path='view',
            skip=False,
            type=vim.view.ContainerView
        )

        obj_spec = vmodl.query.PropertyCollector.ObjectSpec(
            obj=view,
            skip=False,
            selectSet=[traversal]
        )

        path_set = list(set(["name"] + propertyPaths))

        prop_spec = vmodl.query.PropertyCollector.PropertySpec(
            type=objectType,
            pathSet=path_set,
            all=False
        )

        filter_spec = vmodl.query.PropertyCollector.FilterSpec(
            objectSet=[obj_spec],
            propSet=[prop_spec]
        )

        options = vmodl.query.PropertyCollector.RetrieveOptions(maxObjects=100)

        logger.info(f"Initiating data collection for {objectType.__name__} object type from the vCenter.")
        result = pc.RetrievePropertiesEx([filter_spec], options)

        objects = []
        page_count = 0

        while result:
            page_count += 1
            current_objects = result.objects or []
            objects.extend(current_objects)

            logger.debug(f"Reading page: {page_count}. Newly added object is {len(current_objects)}. Total object count: {len(objects)}")

            if result.token:
                result = pc.ContinueRetrievePropertiesEx(result.token)
            else:
                break

        logger.info(f"Successfully collected {len(objects)} {objectType.__name__} objects.")
        return objects

    except vmodl.query.InvalidProperty as e:
        logger.error(f"Invalid property requested for {objectType.__name__}: {e.name}. Nothing is published for it this cycle.")
        raise
    except Exception as e:
        logger.error(f"Failed to read {objectType.__name__} objects from the vCenter: {repr(e)}. Nothing is published for them this cycle.")
        raise
    finally:
        if view is not None:
            try:
                view.Destroy()
            except Exception as e:
                logger.warning(f"Could not release the container view of {objectType.__name__}: {repr(e)}")
