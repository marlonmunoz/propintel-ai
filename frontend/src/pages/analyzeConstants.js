import buildingClassData from '../constants/buildingClasses.json'

export const boroughOptions = [
  'Bronx',
  'Brooklyn',
  'Manhattan',
  'Queens',
  'Staten Island',
]

// Derived from the canonical JSON — single source of truth shared with the
// backend contract test (tests/test_building_class_contract.py).
export const buildingClassOptions = buildingClassData.map(({ value, label }) => ({ value, label }))

// Rental classes require total_units for the dedicated rental model.
export const RENTAL_CLASSES = new Set(
  buildingClassData.filter((c) => c.is_rental).map((c) => c.value)
)

// Classes whose segment model was trained with `residential_units` as a real
// feature (multi-family + both rental segments). For every other class the
// backend ignores the value, so the field is hidden rather than collected and
// discarded. Kept honest against the actual model feature lists by
// tests/test_building_class_contract.py.
export const RESIDENTIAL_UNITS_CLASSES = new Set(
  buildingClassData.filter((c) => c.uses_residential_units).map((c) => c.value)
)

export const initialForm = {
  borough: '',
  neighborhood: '',
  building_class: '',
  year_built: '',
  gross_sqft: '',
  land_sqft: '',
  total_units: '',
  residential_units: '',
  latitude: '',
  longitude: '',
  market_price: '',
}

export const samplePresets = {
  Brooklyn: {
    borough: 'Brooklyn',
    neighborhood: 'Park Slope',
    building_class: '02 TWO FAMILY DWELLINGS',
    year_built: '1925',
    gross_sqft: '1800',
    land_sqft: '2000',
    latitude: '40.6720',
    longitude: '-73.9778',
    market_price: '1250000',
  },
  Manhattan: {
    borough: 'Manhattan',
    neighborhood: 'Upper West Side',
    building_class: '13 CONDOS - ELEVATOR APARTMENTS',
    year_built: '1988',
    gross_sqft: '1100',
    land_sqft: '0',
    latitude: '40.7870',
    longitude: '-73.9754',
    market_price: '1850000',
  },
  Queens: {
    borough: 'Queens',
    neighborhood: 'Astoria',
    building_class: '01 ONE FAMILY DWELLINGS',
    year_built: '1940',
    gross_sqft: '1600',
    land_sqft: '2200',
    latitude: '40.7644',
    longitude: '-73.9235',
    market_price: '980000',
  },
  Bronx: {
    borough: 'Bronx',
    neighborhood: 'Riverdale',
    building_class: '01 ONE FAMILY DWELLINGS',
    year_built: '1935',
    gross_sqft: '2100',
    land_sqft: '3000',
    latitude: '40.9006',
    longitude: '-73.9067',
    market_price: '875000',
  },
  'Staten Island': {
    borough: 'Staten Island',
    neighborhood: 'Tottenville',
    building_class: '01 ONE FAMILY DWELLINGS',
    year_built: '1998',
    gross_sqft: '2400',
    land_sqft: '4200',
    latitude: '40.5084',
    longitude: '-74.2396',
    market_price: '825000',
  },
}

export function getScoreCategory(score) {
  if (score >= 80) return { label: 'Strong',   classes: 'border-lime-500/30 bg-lime-500/15 text-lime-700 dark:text-lime-300' }
  if (score >= 60) return { label: 'Moderate', classes: 'border-cyan-500/30 bg-cyan-500/15 text-cyan-700 dark:text-cyan-300' }
  if (score >= 40) return { label: 'Cautious', classes: 'border-amber-500/30 bg-amber-500/15 text-amber-700 dark:text-amber-300' }
  return            { label: 'Weak',     classes: 'border-rose-500/30 bg-rose-500/15 text-rose-700 dark:text-rose-300' }
}

export function validateForm(formData) {
  const errors = {}

  if (!formData.borough.trim()) errors.borough = 'Borough is required.'
  if (!formData.neighborhood.trim()) errors.neighborhood = 'Neighborhood is required.'
  if (!formData.building_class.trim()) errors.building_class = 'Building class is required.'

  const yearBuilt = Number(formData.year_built)
  if (!formData.year_built) {
    errors.year_built = 'Year built is required.'
  } else if (Number.isNaN(yearBuilt) || yearBuilt < 1800 || yearBuilt > 2026) {
    errors.year_built = 'Enter a valid year built between 1800 and 2026.'
  }

  const grossSqft = Number(formData.gross_sqft)
  if (!formData.gross_sqft) {
    errors.gross_sqft = 'Gross square footage is required.'
  } else if (Number.isNaN(grossSqft) || grossSqft <= 0) {
    errors.gross_sqft = 'Gross square footage must be greater than 0.'
  }

  const landSqft = Number(formData.land_sqft)
  if (!formData.land_sqft) {
    errors.land_sqft = 'Land square footage is required.'
  } else if (Number.isNaN(landSqft) || landSqft < 0) {
    errors.land_sqft = 'Land square footage must be 0 or greater.'
  }

  const latitude = Number(formData.latitude)
  if (!formData.latitude) {
    errors.latitude = 'Latitude is required.'
  } else if (Number.isNaN(latitude) || latitude < 40.0 || latitude > 41.5) {
    errors.latitude = 'Latitude must be within NYC bounds (40.0 – 41.5).'
  }

  const longitude = Number(formData.longitude)
  if (!formData.longitude) {
    errors.longitude = 'Longitude is required.'
  } else if (Number.isNaN(longitude) || longitude < -75.0 || longitude > -73.0) {
    errors.longitude = 'Longitude must be within NYC bounds (−75.0 – −73.0).'
  }

  const marketPrice = Number(formData.market_price)
  if (!formData.market_price) {
    errors.market_price = 'Market price is required.'
  } else if (Number.isNaN(marketPrice) || marketPrice <= 0) {
    errors.market_price = 'Market price must be greater than 0.'
  }

  if (RENTAL_CLASSES.has(formData.building_class)) {
    const totalUnits = Number(formData.total_units)
    if (!formData.total_units) {
      errors.total_units = 'Total units is required for rental valuation.'
    } else if (Number.isNaN(totalUnits) || totalUnits < 1 || !Number.isInteger(totalUnits)) {
      errors.total_units = 'Total units must be a whole number of 1 or more.'
    }
  }

  // Residential units stays optional — an empty value is imputed by the model
  // rather than rejected. Only validate what the user actually typed.
  if (formData.residential_units) {
    const residentialUnits = Number(formData.residential_units)
    const totalUnits = Number(formData.total_units)
    if (
      Number.isNaN(residentialUnits)
      || residentialUnits < 0
      || !Number.isInteger(residentialUnits)
    ) {
      errors.residential_units = 'Residential units must be a whole number of 0 or more.'
    } else if (formData.total_units && !Number.isNaN(totalUnits) && residentialUnits > totalUnits) {
      errors.residential_units = 'Residential units cannot exceed total units.'
    }
  }

  return errors
}
