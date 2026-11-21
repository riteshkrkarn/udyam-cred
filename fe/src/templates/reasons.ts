/**
 * Plain Language Templates for Decision Reasons
 * Maps backend reasoning to user-friendly explanations
 * Mirrors backend app/templates/reasons.py
 */

export interface ReasonTemplates {
  tier_reasons: { [key: string]: string }
  next_tier_criteria: { [key: string]: string }
  error_messages: { [key: string]: string }
}

export const tierReasons: ReasonTemplates['tier_reasons'] = {
  // Tier 1 approval reasons
  sufficient_verified_window:
    'We verified {months} months of your bank data (we need at least 6 months)',
  good_source_agreement:
    'Your bank data, UPI payments, and shop sales align well ({agreement}% agreement)',
  photo_verified: 'We checked your shop photos and verified your location matches your rent agreement',
  
  // Tier 1 rejection reasons
  insufficient_verified_data:
    'We need at least 6 months of bank data to assess your loan. You currently have {months} month(s).',
  weak_source_agreement:
    'Your bank data and shop sales don\'t align well enough ({agreement}% agreement). We need stronger alignment.',
  location_mismatch: 'Your shop location from photos doesn\'t match your rent agreement address.',
  no_photos: 'We need 3 clear photos of your shop with a written code to verify your location.',
  no_gst_tier2:
    'You\'re not registered for GST yet. Registering for GST takes 10 minutes online and unlocks Tier 2 loans (up to ₹2.5L).',
  
  // Tier 2 reasons
  gst_registered:
    'You\'re registered for GST with {months} months of filing history. This shows consistent business sales.',
  tier2_eligible:
    'You qualify for Tier 2! You have {months} months of verified data, GST registration, and good agreement between your sources.',
  
  // Tier 2 rejection reasons
  insufficient_gst_history:
    'We need at least 12 months of GST filing history for Tier 2. You have {months} month(s).',
  gst_not_registered: 'Tier 2 requires GST registration. Registering takes 10 minutes and costs ₹0.',
  
  // Tier 3 reasons
  udyam_registered: 'You have Udyam registration, which shows your business is formally recognized by the government.',
  tier3_eligible:
    'You qualify for Tier 3! Large loans up to ₹10L with 36-month tenure. You have {months} months of GST history, Udyam registration, and a good prior repayment record.',
  
  // Tier 3 rejection reasons
  insufficient_tier3_gst:
    'Tier 3 requires 24+ months of GST history. You currently have {months} month(s).',
  udyam_not_registered: 'Tier 3 requires Udyam registration (takes 10 minutes, free online).',
  no_prior_repayment_history:
    'Tier 3 requires a history of on-time loan repayment with us. You can qualify after 6+ months of on-time payments on a Tier 1 or 2 loan.',
  
  // General approval reasons
  amount_cap_tier1: 'Your Tier 1 loan is capped at ₹50,000 based on your verified business data.',
  amount_cap_tier2: 'Your Tier 2 loan is capped at ₹2,50,000 based on your verified business data and GST filings.',
  amount_cap_tier3: 'Your Tier 3 loan is capped at ₹10,00,000 based on your verified business data and Udyam registration.',
  
  // Data quality reasons
  excellent_data_quality: 'Your data is excellent—all three sources (bank, GST, UPI) align perfectly.',
  good_data_quality: 'Your data quality is good. Bank and GST data agree well.',
  fair_data_quality: 'Your data quality is fair. We have bank data but limited GST history.',
  single_source_data: 'We only have bank data to verify your sales. Adding GST filings would strengthen your application.',
}

export const nextTierCriteria: ReasonTemplates['next_tier_criteria'] = {
  // From Tier 1 to Tier 2
  register_gst_tier2:
    'Register for GST to unlock Tier 2 loans (up to ₹2.5L). It takes 10 minutes online and costs ₹0.',
  maintain_repayment_tier2:
    'Maintain 6+ months of on-time EMI payments. After that, you automatically qualify for Tier 2.',
  extend_verified_history_tier2:
    'Keep your business running for 12 months with consistent sales. We\'ll then have 12 months of verified bank data.',
  
  // From Tier 2 to Tier 3
  register_udyam_tier3:
    'Register for Udyam (free government registration for small businesses). It takes 10 minutes online.',
  maintain_repayment_tier3:
    'After 6+ months of on-time Tier 2 payments, you\'ll qualify for Tier 3 (up to ₹10L).',
  extend_gst_history_tier3:
    'Maintain 24 months of GST filing history. You currently have {months} months.',
  
  // General next-tier criteria
  improve_sales: 'Increase your monthly business sales. Higher sales unlock higher loan amounts.',
  better_documentation:
    'Upload additional documents like bills and GST returns. Better documentation strengthens your application.',
  business_improvement: 'Show consistent or growing business sales over the next few months.',
}

export const errorMessages: ReasonTemplates['error_messages'] = {
  no_consent: 'We need your consent to verify your business data. Please agree to share your bank data.',
  insufficient_documents: 'We need at least an electricity bill or rent receipt to verify your location.',
  photos_incomplete: 'We need 3 clear photos of your shop with a handwritten code visible in each.',
  photo_code_not_visible: 'The written code is not visible in your photo. Please retake the photo with the code clearly visible.',
  location_too_far: 'Your shop location from the photo is {distance}m away from your rent agreement address. Please verify.',
  invalid_photo: 'The photo is too blurry or unclear. Please retake it.',
  gst_mismatch: 'Your GST filing amount doesn\'t match your bank data. Please check your GST records.',
  no_household_data: 'We need information about your monthly household expenses to calculate a safe loan amount.',
  amount_too_high: 'Your requested amount (₹{requested}) exceeds the limit for {tier} (₹{limit}).',
  amount_too_low: 'Your requested amount (₹{requested}) is below the minimum for your tier (₹{minimum}).',
  application_incomplete: 'Your application is incomplete. Please fill in all required fields.',
  temporary_error: 'We\'re having a temporary issue. Please try again in a few moments.',
  server_error: 'Server error. Please contact our support team.',
}

/**
 * Generate plain-language reason for tier decision
 */
export function generateTierReason(
  template: string,
  variables: { [key: string]: string | number }
): string {
  let reason = tierReasons[template as keyof typeof tierReasons] || template

  // Replace all {variable} with actual values
  Object.entries(variables).forEach(([key, value]) => {
    reason = reason.replace(`{${key}}`, String(value))
  })

  return reason
}

/**
 * Generate next-tier criterion
 */
export function generateNextTierCriterion(
  template: string,
  variables: { [key: string]: string | number } = {}
): string {
  let criterion = nextTierCriteria[template as keyof typeof nextTierCriteria] || template

  // Replace all {variable} with actual values
  Object.entries(variables).forEach(([key, value]) => {
    criterion = criterion.replace(`{${key}}`, String(value))
  })

  return criterion
}

/**
 * Generate error message
 */
export function generateErrorMessage(
  template: string,
  variables: { [key: string]: string | number } = {}
): string {
  let message = errorMessages[template as keyof typeof errorMessages] || template

  // Replace all {variable} with actual values
  Object.entries(variables).forEach(([key, value]) => {
    message = message.replace(`{${key}}`, String(value))
  })

  return message
}

/**
 * Convert reason list from backend format to UI format
 * Backend sends: ["verified_10_months", "good_source_agreement", ...]
 * Frontend displays: ["We verified 10 months of your bank data...", ...]
 */
export function formatReasonsList(
  reasons: string[],
  variables?: { [key: string]: { [key: string]: string | number } }
): string[] {
  return reasons.map(reason => {
    const vars = variables?.[reason] || {}
    return generateTierReason(reason, vars)
  })
}

/**
 * Convert next-tier criteria from backend format
 */
export function formatNextTierCriteria(
  criteria: string[],
  variables?: { [key: string]: { [key: string]: string | number } }
): string[] {
  return criteria.map(criterion => {
    const vars = variables?.[criterion] || {}
    return generateNextTierCriterion(criterion, vars)
  })
}
