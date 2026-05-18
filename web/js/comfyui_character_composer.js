import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

const NODE_NAME = "ComfyUICharacterComposer";
const PLACEHOLDER = "Run the node to preview the final prompt here.";

const SECTION_LABELS = {
    "--- CORE CREATIVE ---": "Core Creative",
    "--- CHARACTER LOOK ---": "Character Look",
    "--- CAMERA & FRAMING ---": "Camera & Framing",
    "--- STYLE & SCENE ---": "Style & Scene",
    "--- OPTIONAL EXTRAS ---": "Optional Extras",
};

const ADVANCED_WIDGET_NAMES = new Set([
    "extra_modifiers",
    "smart_preset",
    "fill_auto_traits",
    "reset_overrides",
    "randomize_look_keep_position",
    "bypass_generator",
    "preserve_input_position",
    "preserve_character_look",
    "outfit_mode",
    "age",
    "ethnicity",
    "fantasy_race",
    "camera_gear",
    "style_adjective",
    "creative_twist",
    "background_mood",
    "accessory",
    "prop",
    "background_prop",
]);

const SECTION_ORDER = [
    "--- CORE CREATIVE ---",
    "--- CHARACTER LOOK ---",
    "--- CAMERA & FRAMING ---",
    "--- STYLE & SCENE ---",
    "--- OPTIONAL EXTRAS ---",
];

function unwrapTextValue(value) {
    if (Array.isArray(value)) {
        return value.length ? value[0] : "";
    }
    return value === undefined || value === null ? "" : value;
}

function extractFinalPrompt(message) {
    const output = message?.output ?? message;
    const uiItems = Array.isArray(output) ? output : [output];
    for (const item of uiItems) {
        const text = unwrapTextValue(item?.text);
        if (text !== "") {
            return String(text);
        }
    }
    return "";
}

function getNodeById(id) {
    if (id === undefined || id === null || !app.graph) {
        return null;
    }
    return app.graph.getNodeById?.(id) || app.graph.getNodeById?.(Number(id)) || app.graph._nodes_by_id?.[id] || null;
}

function getWidgetLabel(widget) {
    return widget.label || widget.name || "";
}

function getWidgetDisplayValue(widget) {
    if (getComboOptions(widget).length) {
        const value = widget.value;
        return value === undefined || value === null ? "" : String(value);
    }
    return widget.value === undefined || widget.value === null ? "" : String(widget.value);
}

function getComboOptions(widget) {
    const options = widget?.options;
    if (Array.isArray(options)) {
        return options;
    }
    if (Array.isArray(options?.values)) {
        return options.values;
    }
    if (Array.isArray(options?.options)) {
        return options.options;
    }
    return [];
}

function comboHasValue(widget, value) {
    return getComboOptions(widget).some((option) => String(option) === String(value));
}

function isIntegerLike(value) {
    if (typeof value === "number") {
        return Number.isInteger(value);
    }
    return typeof value === "string" && /^\d+$/.test(value.trim());
}

function isAdvancedToggleWidget(widget) {
    return Boolean(
        widget?._composerToggleAdvanced ||
        widget?.value === "toggle_advanced" ||
        widget?.name === "toggle_advanced" ||
        widget?.name === "Show advanced" ||
        widget?.name === "Hide advanced"
    );
}

function syncAdvancedToggleWidget(widget, visible) {
    if (!widget) {
        return;
    }
    const label = visible ? "Hide advanced" : "Show advanced";
    widget.name = label;
    widget.label = label;
    widget.value = "toggle_advanced";
    widget.serialize = false;
    widget._composerToggleAdvanced = true;
}

function setWidgetValue(widget, value) {
    widget.value = value;
    for (const field of ["element", "domElement", "textarea"]) {
        const target = widget[field];
        if (!target) {
            continue;
        }
        if ("value" in target) {
            target.value = value;
        }
        const input = target.querySelector?.("textarea, input");
        if (input && "value" in input) {
            input.value = value;
        }
    }
}

function repairShiftedWidgetValues(node) {
    const widgets = (node.widgets || []).filter((widget) => !isAdvancedToggleWidget(widget));
    const previewIndex = widgets.findIndex((widget) => widget.name === "final_prompt_preview");
    if (previewIndex < 0) {
        return;
    }

    const preview = widgets[previewIndex];
    const seed = widgets.find((widget) => widget.name === "seed");
    const extraModifiers = widgets.find((widget) => widget.name === "extra_modifiers");
    const generationProfile = widgets.find((widget) => widget.name === "generation_profile");

    if (!preview || !seed || !extraModifiers || !generationProfile) {
        return;
    }

    const looksLikeMissingPreview =
        isIntegerLike(preview.value) &&
        !isIntegerLike(seed.value) &&
        comboHasValue(generationProfile, extraModifiers.value) &&
        !comboHasValue(generationProfile, generationProfile.value);

    if (!looksLikeMissingPreview) {
        return;
    }

    const values = widgets.map((widget) => widget.value);
    for (let i = widgets.length - 1; i > previewIndex + 1; i--) {
        setWidgetValue(widgets[i], values[i - 1]);
    }
    setWidgetValue(preview, node._composerFinalPrompt || PLACEHOLDER);
}

function ensureFinalPromptWidget(node) {
    const widget = node.widgets?.find((w) => w.name === "final_prompt_preview");
    if (!widget) {
        return null;
    }

    widget.label = "Final prompt";
    widget.hidden = false;
    widget.serialize = true;
    widget.disabled = true;
    widget.readonly = true;

    const element = widget.element || widget.domElement || widget.textarea;
    if (element) {
        if ("readOnly" in element) {
            element.readOnly = true;
        }
        if (element.style) {
            element.style.opacity = 0.8;
        }
        if ("placeholder" in element) {
            element.placeholder = PLACEHOLDER;
        }
        const input = element.querySelector?.("textarea, input");
        if (input) {
            input.readOnly = true;
            input.style.opacity = 0.8;
            input.placeholder = PLACEHOLDER;
        }
    }

    const widgets = node.widgets || [];
    const currentIndex = widgets.indexOf(widget);
    if (currentIndex !== -1) {
        widgets.splice(currentIndex, 1);
    }
    const inputPromptIndex = widgets.findIndex((w) => w.name === "input_prompt");
    widgets.splice(inputPromptIndex >= 0 ? inputPromptIndex + 1 : 0, 0, widget);
    return widget;
}

function ensureAdvancedToggleWidget(node) {
    const widgets = node.widgets || [];
    let toggleWidget = null;
    for (let index = widgets.length - 1; index >= 0; index--) {
        const widget = widgets[index];
        if (!isAdvancedToggleWidget(widget)) {
            continue;
        }
        if (!toggleWidget) {
            toggleWidget = widget;
        } else {
            widgets.splice(index, 1);
        }
    }

    if (!toggleWidget) {
        toggleWidget = node.addWidget("button", "Show advanced", "toggle_advanced", () => {
            node._composerAdvancedVisible = !node._composerAdvancedVisible;
            setAdvancedVisibility(node, node._composerAdvancedVisible);
            node.setDirtyCanvas?.(true, true);
            app.graph?.setDirtyCanvas?.(true, true);
        });
    }

    syncAdvancedToggleWidget(toggleWidget, Boolean(node._composerAdvancedVisible));
    return toggleWidget;
}

function updateFinalPromptWidget(node, finalPrompt) {
    if (!node || node.comfyClass !== NODE_NAME && node.type !== NODE_NAME) {
        return;
    }
    if (!finalPrompt) {
        return;
    }
    const widget = ensureFinalPromptWidget(node);
    if (!widget) {
        return;
    }
    setWidgetValue(widget, finalPrompt);
    node._composerFinalPrompt = finalPrompt;
    node.setDirtyCanvas?.(true, true);
    app.graph?.setDirtyCanvas?.(true, true);
}

function setAdvancedVisibility(node, visible) {
    if (!node._composerAdvancedWidgets) return;
    node._composerAdvancedWidgets.forEach((widget) => {
        widget.hidden = !visible;
    });
    const toggleWidget = node.widgets?.find((widget) => isAdvancedToggleWidget(widget));
    syncAdvancedToggleWidget(toggleWidget, visible);
}

function buildSectionData(node) {
    const groups = SECTION_ORDER.map((section) => ({
        section,
        label: SECTION_LABELS[section],
        widgets: [],
    }));

    for (const section of groups) {
        let collecting = false;
        for (const widget of node.widgets || []) {
            if (widget.name === section.section) {
                collecting = true;
                continue;
            }
            if (collecting) {
                if (SECTION_LABELS[widget.name]) {
                    break;
                }
                if (isAdvancedToggleWidget(widget) || widget.name === "final_prompt_preview") {
                    continue;
                }
                section.widgets.push(widget);
            }
        }
    }

    return groups;
}

function setupNode(node) {
    repairShiftedWidgetValues(node);
    ensureFinalPromptWidget(node);

    node._composerAdvancedVisible = Boolean(node._composerAdvancedVisible);
    node._composerAdvancedWidgets = [];
    node._composerSectionWidgets = [];

    for (const widget of node.widgets || []) {
        if (SECTION_LABELS[widget.name]) {
            widget.hidden = true;
            node._composerSectionWidgets.push(widget);
        }
        if (ADVANCED_WIDGET_NAMES.has(widget.name)) {
            widget.hidden = true;
            node._composerAdvancedWidgets.push(widget);
        }
    }

    ensureAdvancedToggleWidget(node);
    setAdvancedVisibility(node, node._composerAdvancedVisible);
}

app.registerExtension({
    name: "ComfyUICharacterComposer.UI",

    setup() {
        api.addEventListener("executed", ({ detail }) => {
            const nodeId = detail?.display_node ?? detail?.node;
            const node = getNodeById(nodeId);
            const finalPrompt = extractFinalPrompt(detail);
            updateFinalPromptWidget(node, finalPrompt);
        });
    },

    beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_NAME) return;

        const origCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            origCreated?.apply(this, arguments);
            setupNode(this);
        };

        const origConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            origConfigure?.apply(this, arguments);
            setupNode(this);
        };

        const origExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (message) {
            origExecuted?.apply(this, arguments);
            updateFinalPromptWidget(this, extractFinalPrompt(message));
        };

        const origDraw = nodeType.prototype.onDrawForeground;
        nodeType.prototype.onDrawForeground = function (ctx) {
            origDraw?.call(this, ctx);
            if (this.flags?.collapsed) return;

            ctx.save();
            ctx.font = "bold 11px Arial";
            ctx.fillStyle = "#89d3ff";
            ctx.textBaseline = "top";

            const padding = 10;
            let drawY = 35;

            const sectionData = buildSectionData(this);
            for (const section of sectionData) {
                const visibleWidgets = section.widgets.filter((widget) => !widget.hidden && widget.type !== "STRING" && widget.type !== "BOOLEAN");
                if (!visibleWidgets.length) continue;

                ctx.fillText(section.label, padding, drawY);
                drawY += 18;
                ctx.font = "11px Arial";
                ctx.fillStyle = "#eef6ff";

                for (const widget of visibleWidgets) {
                    const label = getWidgetLabel(widget);
                    const value = getWidgetDisplayValue(widget);
                    ctx.fillText(`${label}: ${value}`, padding + 6, drawY);
                    drawY += 14;
                }
                drawY += 10;
                ctx.font = "bold 11px Arial";
                ctx.fillStyle = "#89d3ff";
            }

            ctx.restore();
        };
    },
});
