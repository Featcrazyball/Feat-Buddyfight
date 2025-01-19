function formatAbilityText(abilityText) {
    const parts = abilityText.split('■');
    
    const formattedParts = parts.map((part, index) => {
        const dotParts = part.trim().split('・');
        const formattedPart = dotParts.map(p => p.trim()).join('<br>・');
        return index === 0 ? formattedPart : '■' + formattedPart;
    });

    // Join all parts with line breaks
    return formattedParts.join('<br>');
}
