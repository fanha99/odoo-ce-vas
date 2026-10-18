/** @odoo-module */

import {useComponent, useEffect} from "@odoo/owl";

function toTitleCase(str) {
    return str
        .replaceAll(".", " ")
        .replace(
            /\w\S*/g,
            (txt) => `${txt.charAt(0).toUpperCase()}${txt.substr(1).toLowerCase()}`
        );
}

function enrich(component, targetElement, selector, isIFrame = false) {
    let doc = window.document;
    let contentDocument = targetElement;

    // If we are in an iframe, we need to take the right document
    if (isIFrame) {
        contentDocument = targetElement.contentDocument;
        doc = contentDocument;
    }

    // If there are selector, we may have multiple blocks of code to enrich
    const targets = [];
    if (selector) {
        targets.push(...contentDocument.querySelectorAll(selector));
    } else {
        targets.push(contentDocument);
    }

    // Search the elements with the selector, update them and bind an action.
    for (const currentTarget of targets) {
        const elementsToWrap = currentTarget.querySelectorAll("[res-model][domain]");
        for (const element of elementsToWrap.values()) {
            const resModel = element.getAttribute("res-model");
            const domain = element.getAttribute("domain");
            const actionName = element.getAttribute("action-name") || toTitleCase(resModel);
            
            const wrapper = doc.createElement("a");
            wrapper.style.color = element.classList.contains("o_stock_report_qty") ? "#006600" : "#0066cc";
            wrapper.style.textDecoration = "none";
            wrapper.style.cursor = "pointer";
            
            wrapper.addEventListener("click", async (ev) => {
                ev.preventDefault();
                ev.stopPropagation();
                
                // Call server to create action and get its ID
                const orm = component.env.services.orm;
                const actionId = await orm.call(
                    "ir.actions.act_window",
                    "create",
                    [{
                        name: actionName,
                        type: "ir.actions.act_window",
                        res_model: resModel,
                        domain: domain,
                        view_mode: "tree,form",
                        target: "current",
                    }]
                );
                
                // Open in new browser tab with action ID
                const baseUrl = window.location.origin;
                const url = `${baseUrl}/web#action=${actionId}`;
                window.open(url, "_blank");
                
                // Clean up - delete the temporary action after a delay
                setTimeout(async () => {
                    try {
                        await orm.unlink("ir.actions.act_window", [actionId]);
                    } catch (e) {
                        // Ignore errors when cleaning up
                    }
                }, 5000);
            });
            
            element.parentNode.insertBefore(wrapper, element);
            wrapper.appendChild(element);
        }
    }
}

export function useEnrichWithActionLinks(ref, selector = null) {
    const comp = useComponent();
    useEffect(
        (element) => {
            // If we get an iframe, we need to wait until everything is loaded
            if (element && element.matches && element.matches("iframe")) {
                element.addEventListener("load", () =>
                    enrich(comp, element, selector, true)
                );
            } else if (element) {
                enrich(comp, element, selector);
            }
        },
        () => [ref.el]
    );
}
